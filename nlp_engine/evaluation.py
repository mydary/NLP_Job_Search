"""Evaluasi mesin pencarian dengan penilaian relevansi bertingkat (qrels.csv: 1 = cukup, 2 = sangat relevan).

Catatan tentang Recall@K: bila sebuah kueri punya puluhan lowongan relevan, Recall@10 tidak mungkin
mendekati 1. Karena itu dipakai recall terbatas: hit / min(K, jumlah relevan), yaitu bagian dari
hasil maksimum yang bisa dicapai pada K posisi.
"""
import math
from collections import defaultdict

import numpy as np
import pandas as pd


def load_qrels(path):
    df = pd.read_csv(path)
    qrels = defaultdict(dict)
    for r in df.itertuples(index=False):
        qrels[r.query_id][r.job_id] = int(r.relevance)
    return qrels


def precision_at_k(ranked, rel, k):
    return sum(1 for d in ranked[:k] if rel.get(d, 0) > 0) / k


def recall_at_k(ranked, rel, k):
    total = sum(1 for g in rel.values() if g > 0)
    if not total:
        return 0.0
    return sum(1 for d in ranked[:k] if rel.get(d, 0) > 0) / min(k, total)


def mrr_at_k(ranked, rel, k):
    for i, d in enumerate(ranked[:k], start=1):
        if rel.get(d, 0) > 0:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, rel, k):
    dcg = sum(rel.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def evaluate_system(search_fn, queries, qrels, job_ids, k=10, ks_p=5):
    """search_fn(query_text) -> daftar posisi dokumen berurutan. Mengembalikan (ringkasan, per_kueri)."""
    rows = []
    for q in queries.itertuples(index=False):
        ranked = [job_ids[i] for i in search_fn(q.query)][:50]
        rel = qrels.get(q.query_id, {})
        rows.append({
            "query_id": q.query_id,
            f"P@{ks_p}": precision_at_k(ranked, rel, ks_p),
            f"Recall@{k}": recall_at_k(ranked, rel, k),
            f"MRR@{k}": mrr_at_k(ranked, rel, k),
            f"NDCG@{ks_p}": ndcg_at_k(ranked, rel, ks_p),
            f"NDCG@{k}": ndcg_at_k(ranked, rel, k),
        })
    per_query = pd.DataFrame(rows).set_index("query_id")
    return per_query.mean().round(3), per_query
