import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("TEPAT_ADMIN_KEY", None)
import tempfile  # noqa: E402
_DB = os.environ.get("TEST_DATABASE_URL") or "sqlite:///" + os.path.join(tempfile.mkdtemp(), "uji.db")
os.environ["TEPAT_DATABASE_URL"] = _DB
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_and_meta(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["jobs"] >= 368
    assert "Jakarta" in client.get("/meta").json()["locations"]


def test_search_understands_and_ranks(client):
    r = client.post("/search", json={"query": "Saya menguasai Python, SQL, Pandas, dan visualisasi data. Fresh graduate di bidang analisis data.", "limit": 5}).json()
    assert r["understood"]["level"] == 1
    assert {"Python", "SQL"} <= set(r["understood"]["skills"])
    assert len(r["results"]) == 5
    scores = [x["match"]["score"] for x in r["results"]]
    assert scores == sorted(scores, reverse=True)
    top = r["results"][0]
    assert {"S", "R", "E", "L", "missing", "explanation"} <= set(top["match"])
    assert any(w in top["job_title"] for w in ("Data", "Analyst", "Intelligence", "Reporting"))


@pytest.mark.parametrize("method", ["hybrid", "bm25", "tfidf", "semantic", "exact"])
def test_every_method(client, method):
    r = client.post("/search", json={"query": "mengelola kampanye iklan online dan media sosial", "method": method, "limit": 3})
    assert r.status_code == 200 and r.json()["results"]


def test_filters_apply(client):
    r = client.post("/search", json={"query": "data analyst", "filters": {"location": "Bandung", "employment_type": "Full-time"}, "limit": 20}).json()
    assert r["results"] and all(x["location"] == "Bandung" and x["employment_type"] == "Full-time" for x in r["results"])


def test_user_skills_merge_into_gap(client):
    r = client.post("/search", json={"query": "analisis data", "user_skills": ["SQL", "Microsoft Excel"], "limit": 3}).json()
    assert {"SQL", "Microsoft Excel"} <= set(r["understood"]["skills"])


def test_empty_query_lists_latest(client):
    r = client.post("/search", json={"query": "", "limit": 3}).json()
    assert len(r["results"]) == 3 and r["results"][0]["match"] is None


def test_validation(client):
    assert client.post("/search", json={"query": "x", "method": "nope"}).status_code == 422
    assert client.post("/search", json={"query": "x", "filters": {"experience_level": "Dewa"}}).status_code == 422
    assert client.get("/jobs/J9999").status_code == 404


def test_jobs_and_skills(client):
    j = client.get("/jobs", params={"limit": 2}).json()
    assert j["total"] >= 368 and len(j["items"]) == 2
    one = client.get(f"/jobs/{j['items'][0]['job_id']}").json()
    assert one["job_title"]
    assert any(s["skill_name"] == "Microsoft Excel" and "ms excel" in s["aliases"] for s in client.get("/skills").json())
    assert client.post("/extract-skills", json={"text": "bisa MS Excel dan Postgre SQL"}).json()["skills"] == ["Microsoft Excel", "PostgreSQL"]


def test_admin_add_search_delete(client):
    body = {"job_title": "Quantum Fermentation Analyst", "company": "Lab Uji", "description": "Menganalisis fermentasi kuantum memakai Python dan SQL.",
            "experience_level": "Junior", "location": "Jakarta", "employment_type": "Full-time"}
    r = client.post("/admin/jobs", json=body)
    assert r.status_code == 201
    new_id = r.json()["job_id"]
    found = client.post("/search", json={"query": "Quantum Fermentation Analyst", "method": "bm25", "limit": 3}).json()["results"]
    assert found and found[0]["job_id"] == new_id and set(found[0]["required_skills"]) == {"Python", "SQL"}
    assert client.delete(f"/admin/jobs/{new_id}").status_code == 204
    assert client.get(f"/jobs/{new_id}").status_code == 404


def test_admin_stats_and_evaluate(client):
    assert client.get("/admin/stats").json()["jobs"] >= 368
    ev = client.get("/admin/evaluate").json()
    assert set(ev) == {"hybrid", "bm25", "tfidf", "semantic", "exact"} and 0 < ev["bm25"]["NDCG@5"] <= 1


def test_admin_key_enforced(client, monkeypatch):
    monkeypatch.setenv("TEPAT_ADMIN_KEY", "rahasia")
    assert client.get("/admin/stats").status_code == 401
    assert client.get("/admin/stats", headers={"X-Admin-Key": "rahasia"}).status_code == 200


def test_meta_families_and_family_field(client):
    fam = client.get("/meta").json()["families"]
    assert fam.get("data", 0) > 0 and sum(fam.values()) >= 360
    assert client.get("/jobs", params={"limit": 1}).json()["items"][0]["family"]


def test_understood_has_employment_type(client):
    u = client.post("/search", json={"query": "mau magang di Jakarta", "limit": 1}).json()["understood"]
    assert u["employment_type"] == "Magang" and u["location"] == "Jakarta" and u["level"] == 0


def test_match_endpoint_uses_semantic_relevance(client):
    jid = client.post("/search", json={"query": "data analyst", "limit": 1}).json()["results"][0]["job_id"]
    r = client.post(f"/jobs/{jid}/match", params={"level": 1, "location": "Jakarta"}, json=["Python", "SQL"])
    assert r.status_code == 200
    m = r.json()
    assert m["R"] > 0 and 0 < m["score"] <= 99 and "explanation" in m


def test_health_reports_database(client):
    assert client.get("/health").json()["database"] in ("sqlite", "postgresql")


def test_added_job_survives_restart(client):
    from nlp_engine.engine import SearchEngine
    from nlp_engine.store import JobStore
    from app.main import ROOT
    body = {"job_title": "Penguji Ketahanan Data", "company": "Lab Uji", "description": "Menguji ketahanan penyimpanan data.",
            "experience_level": "Junior", "location": "Jakarta", "employment_type": "Full-time", "salary_min": 7, "salary_max": 9}
    jid = client.post("/admin/jobs", json=body).json()["job_id"]
    e2 = SearchEngine(ROOT, "lsa", JobStore(_DB, os.path.join(ROOT, "dataset", "jobs.csv"), os.path.join(ROOT, "dataset", "skills.csv")))  # "restart": engine baru, database sama
    j = e2.get_job(jid)
    import json
    json.dumps(j, allow_nan=False)  # tidak boleh ada NaN yang merusak respons JSON
    assert j and j["job_title"] == "Penguji Ketahanan Data" and j["salary_max"] == 9.0
    assert e2.get_job("J0001")["required_skills"] and e2.get_job("J0001")["family"]
    client.delete(f"/admin/jobs/{jid}")
    e3 = SearchEngine(ROOT, "lsa", JobStore(_DB, os.path.join(ROOT, "dataset", "jobs.csv"), os.path.join(ROOT, "dataset", "skills.csv")))
    assert e3.get_job(jid) is None and len(e3.jobs) >= 368


def test_alias_and_skill_dictionary_persist(client):
    from nlp_engine.engine import SearchEngine
    from nlp_engine.store import JobStore
    from app.main import ROOT
    assert client.post("/extract-skills", json={"text": "mahir lembar hitung"}).json()["skills"] == []
    r = client.post("/admin/skills/Microsoft Excel/aliases", json={"alias": "Lembar Hitung"})
    assert r.status_code == 201
    assert client.post("/extract-skills", json={"text": "mahir lembar hitung"}).json()["skills"] == ["Microsoft Excel"]
    assert client.post("/admin/skills/Microsoft Excel/aliases", json={"alias": "excel"}).status_code == 409
    assert client.post("/admin/skills/Python/aliases", json={"alias": "lembar hitung"}).status_code == 409
    assert client.post("/admin/skills/Tidak Ada/aliases", json={"alias": "x"}).status_code == 404
    assert client.post("/admin/skills/Python/aliases", json={"alias": "  "}).status_code == 422
    r = client.post("/admin/skills", json={"skill_name": "Prometheus", "category": "DevOps", "aliases": ["prom monitoring"]})
    assert r.status_code == 201
    assert client.post("/admin/skills", json={"skill_name": "prometheus"}).status_code == 409
    assert client.post("/extract-skills", json={"text": "pakai prom monitoring"}).json()["skills"] == ["Prometheus"]
    sk = {s["skill_name"]: s for s in client.get("/skills").json()}
    assert "lembar hitung" in sk["Microsoft Excel"]["aliases"] and sk["Prometheus"]["aliases"] == ["prom monitoring"]
    e2 = SearchEngine(ROOT, "lsa", JobStore(_DB, os.path.join(ROOT, "dataset", "jobs.csv"), os.path.join(ROOT, "dataset", "skills.csv")))
    assert e2.ex.extract("mahir lembar hitung dan prom monitoring") == ["Microsoft Excel", "Prometheus"]


def test_admin_login_flow(client):
    from app import auth
    from app.main import _throttle, engine
    st = engine().store
    st.set_admin("dary", auth.hash_password("sandi-panjang-1"))
    try:
        assert client.get("/health").json()["admin_protected"] is True
        assert client.get("/admin/stats").status_code == 401                      # terkunci tanpa token
        assert client.post("/search", json={"query": "data"}).status_code == 200  # pencarian tetap publik
        assert client.post("/auth/login", json={"username": "dary", "password": "salah"}).status_code == 401
        assert client.post("/auth/login", json={"username": "tidak-ada", "password": "x"}).status_code == 401
        r = client.post("/auth/login", json={"username": "dary", "password": "sandi-panjang-1"})
        assert r.status_code == 200
        tok = r.json()["token"]
        h = {"Authorization": "Bearer " + tok}
        assert client.get("/admin/stats", headers=h).status_code == 200
        assert client.get("/auth/me", headers=h).status_code == 200
        assert client.get("/admin/stats", headers={"Authorization": "Bearer " + tok[:-2] + "xx"}).status_code == 401
        old = auth.make_token("dary", ttl=-1)["token"]
        assert client.get("/admin/stats", headers={"Authorization": "Bearer " + old}).status_code == 401
        assert "scrypt$" in st.get_admin_hash("dary") and "sandi-panjang-1" not in st.get_admin_hash("dary")
        for _ in range(5):
            client.post("/auth/login", json={"username": "dary", "password": "salah"})
        assert client.post("/auth/login", json={"username": "dary", "password": "sandi-panjang-1"}).status_code == 429
    finally:
        st.delete_admin("dary")
        _throttle.fails.clear()
    assert client.get("/admin/stats").status_code == 200  # tanpa akun dan tanpa kunci, admin terbuka lagi (mode pengembangan)


def test_past_internship_is_not_a_search_for_internship(client):
    u = lambda q: client.post("/search", json={"query": q, "limit": 1}).json()["understood"]
    assert u("mau magang di bidang data")["employment_type"] == "Magang"
    for q in ("saya pernah magang 3 bulan, sekarang cari kerja data analyst", "pengalaman magang di startup, lulusan baru"):
        x = u(q)
        assert x["employment_type"] is None and x["level"] != 0, q
    assert u("pernah magang tapi sekarang mau magang lagi di bidang desain")["employment_type"] == "Magang"


def test_level_gate_demotes_internships_from_other_fields(client):
    r = client.post("/search", json={"query": "Saya mau magang di bidang analisis data", "limit": 10}).json()["results"]
    top = [x for x in r[:5]]
    assert sum(x["family"] in ("data", "bi") for x in top) >= 4, [(x["job_title"], x["family"]) for x in top]
    off = next((x for x in r if x["employment_type"] == "Magang" and x["family"] not in ("data", "bi")), None)
    assert off is None or off["match"]["E"] < 100
