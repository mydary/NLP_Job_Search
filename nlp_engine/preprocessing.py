"""Fase 2: praproses teks.

Urutan yang dipakai di seluruh proyek:
    teks mentah -> normalize_text -> (kanonisasi skill, lihat skills.py) -> tokenize -> stem
"""
import re
import unicodedata

# Kata penghubung yang kurang informatif. Kata negasi (tanpa, bukan, tidak, not, without)
# SENGAJA tidak dimasukkan, karena bisa membalik makna persyaratan.
STOPWORDS = set("""
yang dan di ke dari untuk dengan pada dalam atau adalah ini itu akan bisa dapat sebagai juga serta
kami anda kamu saya aku ingin mau mencari cari pekerjaan kerja bekerja lowongan bidang sedang lagi
menggunakan sebuah suatu para oleh agar sehingga karena jika bila sudah telah belum masih sangat
lebih paling kepada bagi antara atas bawah hingga sampai setiap semua beberapa banyak
the a an and or for of in to with we are is looking our you will be as on at by that this it
your their his her from into per than then also can may must should would
""".split())

NEGATIONS = {"tanpa", "bukan", "tidak", "not", "without", "no"}

# Awalan di- dan ke- tidak dipakai: terlalu sering memotong kata asing (digital, kesehatan, diskusi).
_PREFIXES = ("meng", "meny", "mem", "men", "peng", "peny", "pem", "pen", "ber", "ter", "per", "pe")
_SUFFIXES = ("nya", "kah", "kan", "an")


def normalize_text(text: str) -> str:
    """Huruf kecil, samakan unicode, buang tanda baca, rapikan spasi.

    Tanda yang bermakna pada nama skill (+ # . /) dipertahankan sampai tahap kanonisasi skill.
    """
    text = unicodedata.normalize("NFKC", str(text)).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9+#./_\s-]", " ", text)
    text = re.sub(r"(?<![a-z0-9])[./-]+|[./-]+(?![a-z0-9])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem(token: str) -> str:
    """Stemmer Indonesia sederhana (aturan imbuhan). Token skill (sk_...) tidak diubah.

    Ini sengaja dibuat ringan agar mudah dipahami. Latihan: ganti dengan Sastrawi dan bandingkan
    hasil evaluasinya.
    """
    if token.startswith("sk_") or len(token) <= 5 or any(c.isdigit() for c in token):
        return token
    out = token
    for suf in _SUFFIXES:
        if out.endswith(suf) and len(out) - len(suf) >= 4:
            out = out[: -len(suf)]
            break
    for pre in _PREFIXES:
        if out.startswith(pre) and len(out) - len(pre) >= 4:
            out = out[len(pre):]
            break
    return out


def tokenize(text: str, remove_stopwords: bool = True, do_stem: bool = True) -> list:
    tokens = re.findall(r"[a-z0-9_+#]+", text)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    if do_stem:
        tokens = [stem(t) for t in tokens]
    return tokens


def preprocess(text: str, extractor=None) -> list:
    """Jalur lengkap. Bila `extractor` (SkillExtractor) diberikan, alias skill disatukan lebih dulu."""
    t = normalize_text(text)
    if extractor is not None:
        t = extractor.canonicalize(t)
    return tokenize(t)
