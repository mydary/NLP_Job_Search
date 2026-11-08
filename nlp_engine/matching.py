"""Fase 5: pemahaman kueri, skor kecocokan, dan analisis kekurangan skill.

    Skor = 0.40 S + 0.30 R + 0.20 E + 0.10 L
    S skill match, R relevansi semantik, E kecocokan pengalaman, L kecocokan lokasi.
Bobot ini hipotesis awal dan perlu diuji, bukan bobot universal. Skor bukan peluang diterima kerja.
"""
import re

LEVELS = ["Internship", "Entry Level", "Junior", "Mid-level", "Senior"]
LOCATIONS = ["Jakarta", "Bandung", "Surabaya", "Yogyakarta", "Serang", "Tangerang", "Bekasi", "Semarang", "Denpasar", "Remote"]
WEIGHTS = {"S": 0.40, "R": 0.30, "E": 0.20, "L": 0.10}
# E dan L hanya berarti bila bidang lowongan cocok. Di bawah GATE_R (relevansi semantik, 0-100) keduanya dikecilkan
# sebanding, supaya "magang di bidang data" tidak memunculkan magang di bidang lain hanya karena levelnya sama.
# Nilai 40 adalah hipotesis untuk skala cosine LSA, perlu diuji ulang bila backend semantik diganti.
GATE_R = 40.0
# "pernah magang", "pengalaman magang 3 bulan": menyebut magang sebagai riwayat, bukan sebagai yang dicari.
_PAST_INTERN = re.compile(r"(pernah|sudah|telah|selesai|habis|setelah|alumni|pengalaman)\s+(?:\w+\s+){0,2}?(magang|intern\w*)")


def understand_query(text, extractor):
    """Ambil skill, level, lokasi, dan jenis pekerjaan dari kalimat bebas (aturan sederhana)."""
    t = text.lower()
    seek = _PAST_INTERN.sub(" ", t)  # teks untuk mendeteksi niat mencari magang
    level = None
    if re.search(r"magang|intern", seek):
        level = 0
    elif re.search(r"senior|\blead\b|kepala", t):
        level = 4
    elif re.search(r"\bjunior\b|\bjr\b", t):
        level = 2
    elif re.search(r"fresh|lulusan baru|baru lulus|pemula|entry|tanpa pengalaman|no formal experience", t):
        level = 1
    elif re.search(r"\bmid\b|menengah", t):
        level = 3
    else:
        m = re.search(r"(\d+)\s*\+?\s*(tahun|thn|years?|yrs?)", t)
        if m:
            y = int(m.group(1))
            level = 1 if y <= 1 else 2 if y <= 2 else 3 if y <= 5 else 4
    emp = ("Magang" if re.search(r"magang|intern", seek) else "Part-time" if re.search(r"part[- ]?time|paruh waktu", t)
           else "Kontrak" if re.search(r"kontrak|freelance", t) else "Full-time" if re.search(r"full[- ]?time|penuh waktu", t) else None)
    loc = "Remote" if re.search(r"remote|wfh|jarak jauh", t) else next(
        (L for L in LOCATIONS if re.search(r"(?<![a-z])" + L.lower() + r"(?![a-z])", t)), None)
    return {"skills": extractor.extract(text), "level": level, "location": loc, "employment_type": emp}


def _skill_status(required, preferred, have):
    have = set(have)
    return ([(s, s in have) for s in required], [(s, s in have) for s in preferred])


def match_job(job, user_skills, semantic_cos, level=None, location=None):
    """job: baris jobs.csv (dict). semantic_cos: kemiripan cosine kueri-lowongan (0..1)."""
    req = [s for s in str(job["required_skills"]).split(";") if s and s != "nan"]
    pref = [s for s in str(job["preferred_skills"]).split(";") if s and s != "nan"]
    have = set(user_skills)
    cov = lambda lst: (sum(s in have for s in lst) / len(lst)) if lst else None
    if not have:
        S = None
    else:
        a, b = cov(req), cov(pref)
        S = 100 * (a if b is None else 0.85 * a + 0.15 * b)
    R = min(100.0, 100 * max(0.0, float(semantic_cos)))
    if S is None:
        S = R
    jl = LEVELS.index(job["experience_level"])
    E = 70 if level is None else {0: 100, 1: 65, 2: 30}.get(abs(level - jl), 10)
    L = 80 if location is None else 100 if job["location"] == location else 90 if job["location"] == "Remote" else 35
    gate = min(1.0, R / GATE_R)
    E, L = round(E * gate), round(L * gate)
    score = WEIGHTS["S"] * S + WEIGHTS["R"] * R + WEIGHTS["E"] * E + WEIGHTS["L"] * L
    missing = [s for s in req + pref if s not in have]
    matched = [s for s in req + pref if s in have]
    parts = []
    if matched:
        parts.append("Cocok karena " + ", ".join(matched[:3]) + " sesuai dengan persyaratan.")
    if missing:
        parts.append("Skill belum dimiliki: " + ", ".join(missing) + ".")
    if gate < 1 and (level is not None or location is not None):
        parts.append("Kecocokan level dan lokasi dihitung sebagian karena bidangnya kurang cocok.")
    return {"score": round(min(99.0, score), 1), "S": round(S), "R": round(R), "E": E, "L": L,
            "missing": missing, "explanation": " ".join(parts) or "Kecocokan rendah."}
