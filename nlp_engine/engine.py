"""SearchEngine: menyatukan seluruh komponen nlp_engine menjadi satu objek yang dipanggil oleh backend.

Indeks dibangun sekali saat start. Menambah atau menghapus lowongan membangun ulang indeks (cukup untuk
ribuan lowongan; untuk skala lebih besar, ganti dengan pembaruan inkremental).
"""
import math
import threading
import time

import numpy as np
import pandas as pd

from .evaluation import evaluate_system
from .matching import LEVELS, match_job, understand_query
from .pipeline import job_text, load_data
from .preprocessing import preprocess
from .skills import SkillExtractor
from .retrieval import BM25, ExactKeyword, InvertedIndex, SemanticRetriever, TfidfRetriever, rrf

METHODS = ("hybrid", "bm25", "tfidf", "semantic", "exact")


def _list(v):
    return [s for s in str(v).split(";") if s and s != "nan"]


def _txt(v):
    return None if pd.isna(v) else str(v)


def _num(v):
    return None if pd.isna(v) else float(v)


class SearchEngine:
    def __init__(self, root=".", semantic_backend="auto", store=None):
        """store: JobStore opsional. Bila ada, lowongan dibaca dari dan ditulis ke database."""
        self.root = root
        self.semantic_backend = semantic_backend
        self.store = store
        self.jobs, self.queries, self.qrels, self.ex = load_data(root)
        if store is not None:
            self.jobs = store.load()
            self.ex = SkillExtractor(store.load_skills())
        self._lock = threading.RLock()
        self._build()

    # ------------------------------------------------------------------ indeks
    def _build(self):
        with self._lock:
            self.jobs = self.jobs.reset_index(drop=True)
            self.job_ids = self.jobs.job_id.tolist()
            self.texts = job_text(self.jobs)
            self.tokens = [preprocess(t, self.ex) for t in self.texts]
            self.index = InvertedIndex(self.tokens)
            self.bm25, self.tfidf = BM25(self.index), TfidfRetriever(self.index)
            self.exact = ExactKeyword(self.texts)
            self.sem = SemanticRetriever(self.semantic_backend)
            self.sem.fit(self.texts if self.sem.requested == "sbert" else [" ".join(t) for t in self.tokens])
            self.sem_backend = self.sem.backend
            self._pos = {j: i for i, j in enumerate(self.job_ids)}

    def _sem_query(self, q):
        return q if self.sem_backend == "sbert" else " ".join(preprocess(q, self.ex))

    # ------------------------------------------------------------------ peringkat
    def rank(self, query, method="hybrid", depth=100):
        if method not in METHODS:
            raise ValueError(f"method harus salah satu dari {METHODS}")
        qt = preprocess(query, self.ex)
        if method == "bm25":
            return self.bm25.search(qt, depth)
        if method == "tfidf":
            return self.tfidf.search(qt, depth)
        if method == "semantic":
            return self.sem.search(self._sem_query(query), depth)
        if method == "exact":
            return self.exact.search(query, depth)
        return rrf([self.bm25.search(qt, 30), self.sem.search(self._sem_query(query), 30)], top=depth)

    # ------------------------------------------------------------------ format
    def job_dict(self, i):
        r = self.jobs.iloc[i]
        return {
            "job_id": r.job_id, "job_title": r.job_title, "company": r.company, "location": r.location,
            "experience_level": r.experience_level, "employment_type": r.employment_type,
            "salary_min": _num(r.salary_min), "salary_max": _num(r.salary_max),
            "posted_at": _txt(r.posted_at), "deadline": _txt(r.deadline),
            "required_skills": _list(r.required_skills), "preferred_skills": _list(r.preferred_skills),
            "description": _txt(r.description),
            "family": "" if pd.isna(r.family) else str(r.family),
        }

    def _passes(self, i, f):
        r = self.jobs.iloc[i]
        if f.get("location") and r.location != f["location"]:
            return False
        if f.get("experience_level") and r.experience_level != f["experience_level"]:
            return False
        if f.get("employment_type") and r.employment_type != f["employment_type"]:
            return False
        if f.get("min_salary"):
            smax = _num(r.salary_max)
            if smax is not None and smax < f["min_salary"]:
                return False
        return True

    # ------------------------------------------------------------------ pencarian
    def search(self, query, method="hybrid", filters=None, user_skills=None, limit=10, offset=0):
        t0 = time.perf_counter()
        filters = {k: v for k, v in (filters or {}).items() if v not in (None, "", 0)}
        with self._lock:
            u = understand_query(query, self.ex)
            skills = list(dict.fromkeys(list(user_skills or []) + u["skills"]))
            if not query.strip():
                order = sorted(range(len(self.jobs)), key=lambda i: str(self.jobs.posted_at[i]), reverse=True)
                results = [{**self.job_dict(i), "match": None} for i in order if self._passes(i, filters)]
                total = len(results)
                return {"understood": {**u, "skills": skills}, "total": total, "method": method,
                        "semantic_backend": self.sem_backend, "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "results": results[offset:offset + limit]}
            ranked = [i for i in self.rank(query, method) if self._passes(i, filters)]
            cos = self.sem.scores(self._sem_query(query))
            bm_rank = {d: n for n, d in enumerate(self.bm25.search(preprocess(query, self.ex), 100), 1)}
            sem_rank = {d: n for n, d in enumerate(self.sem.search(self._sem_query(query), 100), 1)}
            rows = []
            for pos, i in enumerate(ranked):
                m = match_job(self.jobs.iloc[i].to_dict(), skills, cos[i], u["level"], u["location"])
                rows.append((pos, i, m))
            if method == "hybrid":  # skor kecocokan menentukan urutan akhir; RRF hanya memilih kandidat
                rows.sort(key=lambda r: (-r[2]["score"], r[0]))
            results = [{**self.job_dict(i), "match": {**m, "bm25_rank": bm_rank.get(i), "semantic_rank": sem_rank.get(i)}}
                       for _, i, m in rows]
            return {"understood": {**u, "skills": skills}, "total": len(results), "method": method,
                    "semantic_backend": self.sem_backend, "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "results": results[offset:offset + limit]}

    def semantic_cos(self, i, query):
        with self._lock:
            return float(self.sem.scores(self._sem_query(query))[i])

    def families(self):
        with self._lock:
            return {k: int(v) for k, v in self.jobs.family.fillna("").replace("", np.nan).dropna().value_counts().items()}

    def get_job(self, job_id):
        i = self._pos.get(job_id)
        return None if i is None else self.job_dict(i)

    def list_jobs(self, filters=None, limit=20, offset=0):
        filters = {k: v for k, v in (filters or {}).items() if v not in (None, "", 0)}
        with self._lock:
            idx = [i for i in range(len(self.jobs)) if self._passes(i, filters)]
            return len(idx), [self.job_dict(i) for i in idx[offset:offset + limit]]

    # ------------------------------------------------------------------ admin
    def add_job(self, data):
        with self._lock:
            n = max(int(j[1:]) for j in self.job_ids) + 1
            req = data.get("required_skills") or self.ex.extract(data["description"])
            row = {
                "job_id": f"J{n:04d}", "job_title": data["job_title"], "company": data["company"],
                "description": data["description"], "required_skills": ";".join(req),
                "preferred_skills": ";".join(data.get("preferred_skills") or []),
                "experience_level": data["experience_level"], "location": data["location"],
                "employment_type": data["employment_type"], "salary_min": data.get("salary_min"),
                "salary_max": data.get("salary_max"), "posted_at": time.strftime("%Y-%m-%d"),
                "deadline": "", "source": "admin", "family": "", "dup_of": "",
            }
            if self.store is not None:
                self.store.insert(row)
            self.jobs = pd.concat([self.jobs, pd.DataFrame([row])], ignore_index=True)
            self._build()
            return row["job_id"]

    def delete_job(self, job_id):
        with self._lock:
            if job_id not in self._pos:
                return False
            if self.store is not None:
                self.store.delete(job_id)
            self.jobs = self.jobs[self.jobs.job_id != job_id]
            self._build()
            return True

    def stats(self):
        with self._lock:
            j = self.jobs
            return {
                "jobs": len(j), "companies": int(j.company.nunique()), "skills_in_dictionary": len(self.ex.names),
                "indexed_terms": len(self.index.postings), "avg_tokens_per_job": round(self.index.avgdl, 1),
                "semantic_backend": self.sem_backend,
                "by_level": j.experience_level.value_counts().to_dict(),
                "by_location": j.location.value_counts().to_dict(),
                "by_type": j.employment_type.value_counts().to_dict(),
                "top_required_skills": pd.Series([s for v in j.required_skills for s in _list(v)]).value_counts().head(10).to_dict(),
            }

    # ------------------------------------------------------------------ kamus skill
    def _skill_row(self, name):
        for r in self.ex.skills:
            if r["skill_name"].lower() == name.strip().lower():
                return r
        return None

    def _alias_owner(self, alias):
        a = alias.lower()
        for r in self.ex.skills:
            if a == r["skill_name"].lower() or a in [x.strip() for x in str(r["aliases"]).split(";")]:
                return r["skill_name"]
        return None

    def _reload_skills(self):
        if self.store is not None:
            self.ex = SkillExtractor(self.store.load_skills())
        else:
            self.ex = SkillExtractor(pd.DataFrame(self.ex.skills))
        self._build()  # token sk_* di indeks bergantung pada kamus

    def add_alias(self, skill_name, alias):
        """Mengembalikan nama skill baku. ValueError('kosong'|'duplikat'), KeyError bila skill tidak ada."""
        alias = " ".join(alias.lower().split())
        if not alias:
            raise ValueError("kosong")
        with self._lock:
            r = self._skill_row(skill_name)
            if r is None:
                raise KeyError(skill_name)
            if self._alias_owner(alias):
                raise ValueError("duplikat")
            al = [x for x in str(r["aliases"]).split(";") if x] + [alias]
            if self.store is not None:
                self.store.set_aliases(r["skill_name"], al)
            else:
                r["aliases"] = ";".join(al)
            self._reload_skills()
            return r["skill_name"]

    def add_skill(self, name, category, aliases=()):
        name = " ".join(name.split())
        if not name:
            raise ValueError("kosong")
        al = list(dict.fromkeys(" ".join(a.lower().split()) for a in aliases if a.strip()))
        with self._lock:
            if self._alias_owner(name.lower()) or any(self._alias_owner(a) for a in al):
                raise ValueError("duplikat")
            n = max(int(r["skill_id"][1:]) for r in self.ex.skills) + 1
            row = {"skill_id": f"S{n:03d}", "skill_name": name, "category": category or "Lainnya", "aliases": ";".join(al)}
            if self.store is not None:
                self.store.insert_skill(row)
            else:
                self.ex.skills.append(row)
            self._reload_skills()
            return row["skill_id"]

    def evaluate(self):
        out = {}
        for m in METHODS:
            t0 = time.perf_counter()
            summary, _ = evaluate_system(lambda q, m=m: self.rank(q, m, 50), self.queries, self.qrels, self.job_ids)
            out[m] = {**{k: float(v) for k, v in summary.items()},
                      "ms_per_query": round((time.perf_counter() - t0) * 1000 / len(self.queries), 2)}
        return out
