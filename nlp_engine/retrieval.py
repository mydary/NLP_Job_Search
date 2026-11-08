"""Fase 3 dan 4: indeks terbalik, TF-IDF, BM25, pencarian semantik, dan penggabungan RRF.

BM25 dan TF-IDF ditulis dari nol (numpy saja) agar rumusnya terlihat. rank_bm25 dan scikit-learn
dipakai di notebook hanya sebagai pembanding.
"""
import math
from collections import defaultdict

import numpy as np


class InvertedIndex:
    """term -> {doc_id: frekuensi}. doc_id adalah posisi dokumen (0..N-1) pada daftar masukan."""

    def __init__(self, docs_tokens):
        self.N = len(docs_tokens)
        self.doc_len = np.array([len(d) for d in docs_tokens], dtype=float)
        self.avgdl = float(self.doc_len.mean()) if self.N else 0.0
        self.postings = defaultdict(dict)
        for d, toks in enumerate(docs_tokens):
            for t in toks:
                self.postings[t][d] = self.postings[t].get(d, 0) + 1

    def df(self, term):
        return len(self.postings.get(term, {}))

    def boolean_and(self, terms):
        sets = [set(self.postings.get(t, {})) for t in terms]
        return sorted(set.intersection(*sets)) if sets else []

    def boolean_or(self, terms):
        out = set()
        for t in terms:
            out |= set(self.postings.get(t, {}))
        return sorted(out)


def _top(scores, k=None):
    order = np.argsort(-scores, kind="stable")
    order = [int(i) for i in order if scores[i] > 0]
    return order[:k] if k else order


class BM25:
    """Okapi BM25.

        skor(q, d) = sum_t idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * |d| / avgdl))
        idf(t)     = ln(1 + (N - n_t + 0.5) / (n_t + 0.5))
    """

    def __init__(self, index: InvertedIndex, k1=1.5, b=0.75):
        self.ix, self.k1, self.b = index, k1, b

    def idf(self, term):
        n = self.ix.df(term)
        return math.log(1 + (self.ix.N - n + 0.5) / (n + 0.5))

    def scores(self, query_tokens):
        s = np.zeros(self.ix.N)
        for t in set(query_tokens):
            post = self.ix.postings.get(t)
            if not post:
                continue
            idf = self.idf(t)
            for d, tf in post.items():
                norm = self.k1 * (1 - self.b + self.b * self.ix.doc_len[d] / self.ix.avgdl)
                s[d] += idf * tf * (self.k1 + 1) / (tf + norm)
        return s

    def search(self, query_tokens, k=None):
        return _top(self.scores(query_tokens), k)


class TfidfRetriever:
    """TF-IDF (tf log-scaled, idf = ln(N/df)+1) dengan kemiripan cosine."""

    def __init__(self, index: InvertedIndex):
        self.ix = index
        self.idf = {t: math.log(index.N / len(p)) + 1 for t, p in index.postings.items()}
        self.norms = np.zeros(index.N)
        for t, p in index.postings.items():
            for d, tf in p.items():
                self.norms[d] += ((1 + math.log(tf)) * self.idf[t]) ** 2
        self.norms = np.sqrt(self.norms)

    def scores(self, query_tokens):
        q = defaultdict(int)
        for t in query_tokens:
            q[t] += 1
        s = np.zeros(self.ix.N)
        qn = 0.0
        for t, c in q.items():
            if t not in self.ix.postings:
                continue
            qw = (1 + math.log(c)) * self.idf[t]
            qn += qw * qw
            for d, tf in self.ix.postings[t].items():
                s[d] += qw * (1 + math.log(tf)) * self.idf[t]
        denom = (math.sqrt(qn) or 1.0) * np.where(self.norms == 0, 1.0, self.norms)
        return s / denom

    def search(self, query_tokens, k=None):
        return _top(self.scores(query_tokens), k)


class ExactKeyword:
    """E1, baseline paling sederhana: urutkan dokumen menurut jumlah kata kueri yang muncul persis
    (tanpa stemming, tanpa kanonisasi skill, tanpa bobot)."""

    def __init__(self, texts):
        from .preprocessing import STOPWORDS, normalize_text
        self._norm, self._stop = normalize_text, STOPWORDS
        self.sets = [set(normalize_text(t).split()) for t in texts]

    def scores(self, query):
        words = {w for w in self._norm(query).split() if w not in self._stop and len(w) > 2}
        return np.array([len(words & s) for s in self.sets], dtype=float)

    def search(self, query, k=None):
        return _top(self.scores(query), k)


class SemanticRetriever:
    """Pencarian berdasarkan kemiripan makna dengan embedding + cosine similarity.

    backend="sbert": Sentence-BERT (butuh `pip install sentence-transformers` dan akses ke model hub).
    backend="lsa"  : TF-IDF + TruncatedSVD (Latent Semantic Analysis). Tidak butuh unduhan model,
                     berguna sebagai pembanding dan sebagai cadangan saat SBERT tidak tersedia.
    backend="auto" : coba SBERT, jatuh ke LSA bila gagal.
    """

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, backend="auto", model_name=None, n_components=64):
        self.requested, self.model_name, self.n_components = backend, model_name or self.DEFAULT_MODEL, n_components
        self.backend, self.model = None, None
        self.note = ""

    def fit(self, texts):
        if self.requested in ("auto", "sbert"):
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                self.backend = "sbert"
                self.doc_vecs = self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
                return self
            except Exception as e:  # tidak terpasang, atau tidak ada akses ke model hub
                if self.requested == "sbert":
                    raise
                self.note = f"SBERT tidak tersedia ({type(e).__name__}); memakai LSA."
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.backend = "lsa"
        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        X = self.vec.fit_transform(texts)
        self.svd = TruncatedSVD(n_components=min(self.n_components, X.shape[1] - 1), random_state=0)
        self.doc_vecs = self._unit(self.svd.fit_transform(X))
        return self

    @staticmethod
    def _unit(m):
        n = np.linalg.norm(m, axis=1, keepdims=True)
        return m / np.where(n == 0, 1, n)

    def encode(self, texts):
        if self.backend == "sbert":
            return self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return self._unit(self.svd.transform(self.vec.transform(texts)))

    def scores(self, query_text):
        return self.doc_vecs @ self.encode([query_text])[0]

    def search(self, query_text, k=None):
        s = self.scores(query_text)
        order = [int(i) for i in np.argsort(-s, kind="stable") if s[i] > 0]
        return order[:k] if k else order


def rrf(rankings, k=60, top=None):
    """Reciprocal Rank Fusion: skor(d) = sum_r 1 / (k + peringkat_r(d)), peringkat mulai dari 1.

    Memakai peringkat, bukan skor mentah, sehingga skor BM25 dan cosine yang skalanya berbeda
    bisa digabung tanpa normalisasi.
    """
    fused = defaultdict(float)
    for ranking in rankings:
        for pos, d in enumerate(ranking, start=1):
            fused[d] += 1.0 / (k + pos)
    order = sorted(fused, key=lambda d: (-fused[d], d))
    return order[:top] if top else order
