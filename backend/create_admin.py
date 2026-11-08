"""Membuat atau mengganti sandi akun admin.

    python create_admin.py NAMA            (sandi ditanyakan, tidak tampil di layar)
Memakai TEPAT_DATABASE_URL yang sama dengan server. Setelah ada satu akun admin, semua endpoint /admin terkunci.
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from app.auth import hash_password  # noqa: E402
from nlp_engine.store import JobStore  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)
root = os.environ.get("TEPAT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
url = os.environ.get("TEPAT_DATABASE_URL") or "sqlite:///" + os.path.join(root, "backend", "tepat.db")
pw = getpass.getpass("Sandi: ")
if len(pw) < 8 or pw != getpass.getpass("Ulangi sandi: "):
    sys.exit("Sandi minimal 8 karakter dan harus sama.")
JobStore(url, os.path.join(root, "dataset", "jobs.csv"), os.path.join(root, "dataset", "skills.csv")).set_admin(sys.argv[1], hash_password(pw))
print("Akun admin disimpan.")
