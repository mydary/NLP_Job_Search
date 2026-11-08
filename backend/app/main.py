"""API Tepat Karir (FastAPI).

Jalankan dari folder backend/:
    uvicorn app.main:app --reload
Dokumentasi interaktif: http://127.0.0.1:8000/docs

Variabel lingkungan:
    TEPAT_ROOT        folder proyek yang berisi dataset/ (bawaan: satu tingkat di atas backend/)
    TEPAT_SEMANTIC    auto | sbert | lsa (bawaan: auto)
    TEPAT_DATABASE_URL  URL SQLAlchemy, mis. postgresql+psycopg://user:sandi@localhost:5432/tepat
                      (bawaan: sqlite:///backend/tepat.db). Tabel diisi dari dataset/jobs.csv saat masih kosong.
                      Isi "memory" untuk tanpa database (data hilang saat server mati).
    TEPAT_ADMIN_KEY   bila diisi, endpoint /admin mewajibkan header X-Admin-Key dengan nilai ini
"""
import hmac
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = os.environ.get("TEPAT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from app.auth import Throttle, hash_password, make_token, read_token, verify_password  # noqa: E402
from nlp_engine.engine import METHODS, SearchEngine  # noqa: E402
from nlp_engine.store import JobStore  # noqa: E402
from nlp_engine.matching import LEVELS, LOCATIONS  # noqa: E402

TYPES = ["Full-time", "Magang", "Kontrak", "Part-time"]
state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = os.environ.get("TEPAT_DATABASE_URL") or "sqlite:///" + os.path.join(ROOT, "backend", "tepat.db")
    store = None if url == "memory" else JobStore(url, os.path.join(ROOT, "dataset", "jobs.csv"), os.path.join(ROOT, "dataset", "skills.csv"))
    state["engine"] = SearchEngine(ROOT, os.environ.get("TEPAT_SEMANTIC", "auto"), store)
    user, pw = os.environ.get("TEPAT_ADMIN_USER"), os.environ.get("TEPAT_ADMIN_PASSWORD")
    if store is not None and user and pw and store.count_admins() == 0:  # akun admin pertama dari lingkungan
        store.set_admin(user, hash_password(pw))
    yield


app = FastAPI(title="Tepat Karir API", version="0.1.0", lifespan=lifespan,
              description="Pencarian lowongan berbasis skill dan makna (BM25, semantik, hybrid RRF).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def engine() -> SearchEngine:
    return state["engine"]


_throttle = Throttle()


def auth_enabled() -> bool:
    """Admin terkunci bila ada TEPAT_ADMIN_KEY atau minimal satu akun admin di database."""
    e = state.get("engine")
    return bool(os.environ.get("TEPAT_ADMIN_KEY")) or bool(e and e.store is not None and e.store.count_admins())


def require_admin(x_admin_key: Optional[str] = Header(default=None), authorization: Optional[str] = Header(default=None)):
    if not auth_enabled():
        return
    key = os.environ.get("TEPAT_ADMIN_KEY")
    if key and x_admin_key and hmac.compare_digest(x_admin_key, key):
        return
    if authorization and authorization.lower().startswith("bearer ") and read_token(authorization[7:].strip()):
        return
    raise HTTPException(status_code=401, detail="Perlu masuk sebagai admin.", headers={"WWW-Authenticate": "Bearer"})


# ------------------------------------------------------------------ skema
class Filters(BaseModel):
    location: Optional[str] = None
    experience_level: Optional[str] = Field(default=None, description=f"Salah satu dari {LEVELS}")
    employment_type: Optional[str] = Field(default=None, description=f"Salah satu dari {TYPES}")
    min_salary: Optional[float] = Field(default=None, ge=0, description="Gaji maksimum lowongan minimal ini (juta Rp per bulan)")


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=2000, description="Kalimat bebas, daftar skill, atau nama posisi")
    method: str = Field(default="hybrid", description=f"Salah satu dari {list(METHODS)}")
    filters: Filters = Filters()
    user_skills: List[str] = Field(default_factory=list, description="Skill dari profil pengguna (digabung dengan skill dari kueri)")
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class TextRequest(BaseModel):
    text: str = Field(max_length=20000)


class JobIn(BaseModel):
    job_title: str
    company: str
    description: str
    experience_level: str
    location: str
    employment_type: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class SkillIn(BaseModel):
    skill_name: str = Field(min_length=1, max_length=120)
    category: str = "Lainnya"
    aliases: List[str] = []


class AliasIn(BaseModel):
    alias: str = Field(min_length=1, max_length=120)


def _check_choice(value, allowed, name):
    if value and value not in allowed:
        raise HTTPException(status_code=422, detail=f"{name} harus salah satu dari {allowed}")


# ------------------------------------------------------------------ publik
@app.get("/health")
def health():
    e = engine()
    return {"status": "ok", "jobs": len(e.jobs), "semantic_backend": e.sem_backend,
            "database": e.store.dialect if e.store else "memory",
            "admin_protected": auth_enabled()}


@app.get("/meta")
def meta():
    """Nilai yang dipakai untuk mengisi filter di antarmuka."""
    return {"levels": LEVELS, "locations": LOCATIONS, "employment_types": TYPES, "methods": list(METHODS), "families": engine().families()}


@app.post("/search")
def search(req: SearchRequest):
    if req.method not in METHODS:
        raise HTTPException(status_code=422, detail=f"method harus salah satu dari {list(METHODS)}")
    _check_choice(req.filters.experience_level, LEVELS, "experience_level")
    _check_choice(req.filters.employment_type, TYPES, "employment_type")
    return engine().search(req.query, req.method, req.filters.model_dump(), req.user_skills, req.limit, req.offset)


@app.get("/jobs")
def list_jobs(location: Optional[str] = None, experience_level: Optional[str] = None,
              employment_type: Optional[str] = None, min_salary: Optional[float] = Query(default=None, ge=0),
              limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    total, items = engine().list_jobs({"location": location, "experience_level": experience_level,
                                       "employment_type": employment_type, "min_salary": min_salary}, limit, offset)
    return {"total": total, "items": items}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = engine().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan.")
    return job


@app.get("/skills")
def skills():
    e = engine()
    return [{"skill_name": r["skill_name"], "category": r["category"],
             "aliases": [a for a in str(r["aliases"]).split(";") if a and a != "nan"]} for r in e.ex.skills]


@app.post("/extract-skills")
def extract_skills(req: TextRequest):
    """Dipakai untuk membaca skill dari teks CV yang sudah diubah menjadi teks."""
    return {"skills": engine().ex.extract(req.text)}


@app.post("/jobs/{job_id}/match")
def match(job_id: str, skills: List[str] = [], level: Optional[int] = Query(default=None, ge=0, le=4),
          location: Optional[str] = None, query: Optional[str] = Query(default=None, max_length=2000)):
    """Skor kecocokan satu lowongan terhadap skill pengguna (badan permintaan: daftar nama skill).
    Relevansi semantik dihitung dari `query`; bila kosong dipakai kalimat yang dibentuk dari daftar skill."""
    from nlp_engine.matching import match_job
    e = engine()
    i = e._pos.get(job_id)
    if i is None:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan.")
    cos = e.semantic_cos(i, query or ("Saya menguasai " + ", ".join(skills))) if (query or skills) else 0.0
    return match_job(e.jobs.iloc[i].to_dict(), skills, cos, level, location)


# ------------------------------------------------------------------ autentikasi
@app.post("/auth/login")
def login(body: LoginIn, request: Request):
    e = engine()
    if e.store is None:
        raise HTTPException(status_code=501, detail="Akun admin memerlukan database (TEPAT_DATABASE_URL bukan memory).")
    k = (body.username, request.client.host if request.client else "")
    if _throttle.blocked(k):
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan gagal. Coba lagi beberapa menit lagi.")
    stored = e.store.get_admin_hash(body.username)
    # verifikasi tetap dijalankan walau akun tidak ada, agar waktu respons tidak membocorkan nama akun
    ok = verify_password(body.password, stored or "scrypt$00$00")
    if not (stored and ok):
        _throttle.fail(k)
        raise HTTPException(status_code=401, detail="Nama pengguna atau sandi salah.")
    _throttle.ok(k)
    return {**make_token(body.username), "username": body.username}


@app.get("/auth/me", dependencies=[Depends(require_admin)])
def me():
    return {"ok": True}


# ------------------------------------------------------------------ admin
@app.get("/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats():
    return engine().stats()


@app.get("/admin/evaluate", dependencies=[Depends(require_admin)])
def admin_evaluate():
    """Menjalankan 30 kueri uji dan qrels untuk semua metode. Nilai relevansi bersifat sintetis."""
    return engine().evaluate()


@app.post("/admin/jobs", status_code=201, dependencies=[Depends(require_admin)])
def admin_add_job(job: JobIn):
    _check_choice(job.experience_level, LEVELS, "experience_level")
    _check_choice(job.employment_type, TYPES, "employment_type")
    return {"job_id": engine().add_job(job.model_dump())}


@app.delete("/admin/jobs/{job_id}", status_code=204, dependencies=[Depends(require_admin)])
def admin_delete_job(job_id: str):
    if not engine().delete_job(job_id):
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan.")


@app.post("/admin/skills", status_code=201, dependencies=[Depends(require_admin)])
def admin_add_skill(skill: SkillIn):
    """Menambah skill baru ke kamus. Indeks dibangun ulang agar alias langsung berlaku."""
    try:
        return {"skill_id": engine().add_skill(skill.skill_name, skill.category, skill.aliases)}
    except ValueError as e:
        raise HTTPException(status_code=409 if str(e) == "duplikat" else 422,
                            detail="Nama atau alias sudah dipakai skill lain." if str(e) == "duplikat" else "Nama skill kosong.")


@app.post("/admin/skills/{skill_name}/aliases", status_code=201, dependencies=[Depends(require_admin)])
def admin_add_alias(skill_name: str, body: AliasIn):
    try:
        return {"skill_name": engine().add_alias(skill_name, body.alias)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan.")
    except ValueError as e:
        raise HTTPException(status_code=409 if str(e) == "duplikat" else 422,
                            detail="Alias sudah dipakai skill lain." if str(e) == "duplikat" else "Alias kosong.")
