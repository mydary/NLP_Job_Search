"""Penyimpanan lowongan di database (PostgreSQL, atau SQLite untuk pengembangan).

Tabel `jobs` diisi dari dataset/jobs.csv saat pertama kali kosong. Setelah itu database menjadi sumber data:
lowongan yang ditambah atau dihapus lewat API tetap ada setelah server dimulai ulang.
URL contoh:
    postgresql+psycopg://user:sandi@localhost:5432/tepat
    sqlite:///tepat.db
"""
import numpy as np
import pandas as pd
from sqlalchemy import Column, Float, MetaData, String, Table, Text, create_engine, delete, func, insert, select

TEXT_COLS = ["job_title", "company", "description", "required_skills", "preferred_skills", "experience_level",
             "location", "employment_type", "posted_at", "deadline", "source", "family", "dup_of"]
NUM_COLS = ["salary_min", "salary_max"]


class JobStore:
    def __init__(self, url, seed_csv=None, seed_skills_csv=None):
        self.url = url
        self.engine = create_engine(url, future=True, pool_pre_ping=True)
        meta = MetaData()
        self.table = Table("jobs", meta, Column("job_id", String(16), primary_key=True),
                           *[Column(c, Text) for c in TEXT_COLS], *[Column(c, Float) for c in NUM_COLS])
        self.skills = Table("skills", meta, Column("skill_id", String(16), primary_key=True),
                            Column("skill_name", String(120), unique=True, nullable=False),
                            Column("category", Text), Column("aliases", Text))
        self.admins = Table("admins", meta, Column("username", String(60), primary_key=True),
                            Column("password_hash", Text, nullable=False), Column("created_at", String(32)))
        meta.create_all(self.engine)
        with self.engine.begin() as cx:
            empty = cx.execute(select(func.count()).select_from(self.table)).scalar() == 0
        if empty and seed_csv:
            self._seed(seed_csv)
        with self.engine.begin() as cx:
            no_skills = cx.execute(select(func.count()).select_from(self.skills)).scalar() == 0
        if no_skills and seed_skills_csv:
            rows = [self._clean(r) for r in pd.read_csv(seed_skills_csv).to_dict("records")]
            with self.engine.begin() as cx:
                cx.execute(insert(self.skills), rows)

    @property
    def dialect(self):
        return self.engine.dialect.name

    @staticmethod
    def _clean(rec):
        return {k: (None if (v is None or (isinstance(v, float) and np.isnan(v)) or v == "") else v) for k, v in rec.items()}

    def _seed(self, csv_path):
        df = pd.read_csv(csv_path)
        rows = [self._clean(r) for r in df.to_dict("records")]
        with self.engine.begin() as cx:
            cx.execute(insert(self.table), rows)

    def load(self):
        """Seluruh lowongan sebagai DataFrame dengan kolom yang sama seperti jobs.csv (kosong = NaN)."""
        df = pd.read_sql(select(self.table).order_by(self.table.c.job_id), self.engine)
        for c in TEXT_COLS:
            df[c] = df[c].where(df[c].notna() & (df[c] != ""), np.nan)
        return df[["job_id"] + TEXT_COLS[:9] + NUM_COLS + TEXT_COLS[9:]].reset_index(drop=True)

    def insert(self, row):
        with self.engine.begin() as cx:
            cx.execute(insert(self.table), [self._clean(row)])

    def delete(self, job_id):
        with self.engine.begin() as cx:
            cx.execute(delete(self.table).where(self.table.c.job_id == job_id))

    # ---- kamus skill
    def load_skills(self):
        df = pd.read_sql(select(self.skills).order_by(self.skills.c.skill_id), self.engine)
        return df[["skill_id", "skill_name", "category", "aliases"]]

    def insert_skill(self, row):
        with self.engine.begin() as cx:
            cx.execute(insert(self.skills), [self._clean(row)])

    def set_aliases(self, skill_name, aliases):
        from sqlalchemy import update
        with self.engine.begin() as cx:
            cx.execute(update(self.skills).where(self.skills.c.skill_name == skill_name).values(aliases=";".join(aliases)))

    # ---- akun admin
    def count_admins(self):
        with self.engine.begin() as cx:
            return cx.execute(select(func.count()).select_from(self.admins)).scalar()

    def get_admin_hash(self, username):
        with self.engine.begin() as cx:
            return cx.execute(select(self.admins.c.password_hash).where(self.admins.c.username == username)).scalar()

    def set_admin(self, username, password_hash):
        """Membuat akun, atau mengganti sandi bila sudah ada."""
        import time
        with self.engine.begin() as cx:
            if cx.execute(select(self.admins.c.username).where(self.admins.c.username == username)).first():
                from sqlalchemy import update
                cx.execute(update(self.admins).where(self.admins.c.username == username).values(password_hash=password_hash))
            else:
                cx.execute(insert(self.admins), [{"username": username, "password_hash": password_hash,
                                                  "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}])

    def delete_admin(self, username):
        with self.engine.begin() as cx:
            cx.execute(delete(self.admins).where(self.admins.c.username == username))
