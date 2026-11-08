"""Fase 2: ekstraksi skill berbasis kamus + aturan, dengan normalisasi alias ke nama baku."""
import re
import pandas as pd


def slug(name: str) -> str:
    return "sk_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class SkillExtractor:
    """Mencocokkan alias dari skills.csv pada teks. Alias terpanjang dicocokkan lebih dulu,
    sehingga "power bi desktop" tidak terbaca sebagai "power" + "bi"."""

    def __init__(self, skills):
        """skills: path ke skills.csv, atau DataFrame dengan kolom skill_name, category, aliases."""
        df = pd.read_csv(skills) if isinstance(skills, str) else skills.copy()
        df["aliases"] = df["aliases"].fillna("")
        self.skills = df.to_dict("records")
        pairs = []
        for r in self.skills:
            aliases = {r["skill_name"].lower()}
            if isinstance(r["aliases"], str):
                aliases |= {a.strip() for a in r["aliases"].split(";") if a.strip()}
            for a in aliases:
                pairs.append((a, r["skill_name"]))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._patterns = [
            (re.compile(r"(?<![a-z0-9_])" + re.escape(a) + r"(?![a-z0-9_])"), name, a) for a, name in pairs
        ]
        self.names = [r["skill_name"] for r in self.skills]
        self.category = {r["skill_name"]: r["category"] for r in self.skills}

    def canonicalize(self, text: str) -> str:
        """Ganti setiap alias dengan token baku `sk_<nama>`. Teks harus sudah lowercase."""
        for pat, name, _ in self._patterns:
            text = pat.sub(" " + slug(name) + " ", text)
        return text

    def extract(self, text: str) -> list:
        """Daftar nama skill baku yang ditemukan (urut kemunculan pertama, tanpa duplikat)."""
        t = text.lower()
        found = []
        for pat, name, _ in self._patterns:
            m = pat.search(t)
            if m:
                found.append((m.start(), name))
                t = pat.sub(" " * 1 + slug(name) + " ", t)
        found.sort()
        seen, out = set(), []
        for _, n in found:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out
