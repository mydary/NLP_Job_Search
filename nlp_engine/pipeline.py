"""Pembantu kecil agar notebook tidak mengulang kode pemuatan data."""
import os

import pandas as pd

from .evaluation import load_qrels
from .skills import SkillExtractor


def load_data(root=".."):
    """Mengembalikan (jobs, queries, qrels, extractor). `root` = folder proyek (berisi dataset/)."""
    d = os.path.join(root, "dataset")
    jobs = pd.read_csv(os.path.join(d, "jobs.csv"))
    queries = pd.read_csv(os.path.join(d, "queries.csv"))
    qrels = load_qrels(os.path.join(d, "qrels.csv"))
    extractor = SkillExtractor(os.path.join(d, "skills.csv"))
    return jobs, queries, qrels, extractor


def job_text(jobs):
    """Teks yang diindeks untuk tiap lowongan: judul (dua kali, agar lebih berbobot), skill wajib, deskripsi."""
    return (jobs.job_title + " . " + jobs.job_title + " . "
            + jobs.required_skills.fillna("").str.replace(";", " ") + " . " + jobs.description).tolist()
