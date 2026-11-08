"""Autentikasi admin tanpa pustaka tambahan: hash sandi scrypt dan token bertanda tangan HMAC.

Token berisi nama pengguna dan waktu kedaluwarsa, ditandatangani dengan TEPAT_SECRET. Bila TEPAT_SECRET tidak diisi,
kunci acak dibuat setiap server start sehingga semua token lama tidak berlaku lagi setelah restart.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

TOKEN_TTL = 12 * 3600
_SECRET = (os.environ.get("TEPAT_SECRET") or secrets.token_hex(32)).encode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got.hex(), h)
    except Exception:
        return False


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def make_token(username: str, ttl: int = TOKEN_TTL) -> dict:
    exp = int(time.time()) + ttl
    body = _b64(json.dumps({"u": username, "exp": exp}).encode())
    sig = _b64(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())
    return {"token": f"{body}.{sig}", "expires_at": exp}


def read_token(token: str):
    """Nama pengguna bila token sah dan belum kedaluwarsa, selain itu None."""
    try:
        body, sig = token.split(".")
        want = _b64(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, want):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return data["u"] if data["exp"] > time.time() else None
    except Exception:
        return None


class Throttle:
    """Membatasi percobaan masuk yang gagal: 5 kali per 5 menit untuk tiap kombinasi pengguna dan alamat klien."""

    def __init__(self, limit=5, window=300):
        self.limit, self.window, self.fails = limit, window, {}

    def blocked(self, key):
        now = time.time()
        self.fails[key] = [t for t in self.fails.get(key, []) if now - t < self.window]
        return len(self.fails[key]) >= self.limit

    def fail(self, key):
        self.fails.setdefault(key, []).append(time.time())

    def ok(self, key):
        self.fails.pop(key, None)
