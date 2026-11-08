# Backend Tepat Karir (FastAPI)

API tipis di atas `nlp_engine/`. Seluruh logika pencarian ada di `nlp_engine/engine.py`; `app/main.py` hanya
menangani validasi, rute, dan format respons.

## Menjalankan

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Dokumentasi interaktif otomatis di http://127.0.0.1:8000/docs.

Variabel lingkungan: `TEPAT_ROOT` (folder proyek, bawaan satu tingkat di atas `backend/`), `TEPAT_SEMANTIC`
(`auto`, `sbert`, atau `lsa`), `TEPAT_ADMIN_KEY` (bila diisi, `/admin/*` mewajibkan header `X-Admin-Key`).

## Endpoint

| Metode | Rute | Fungsi |
| --- | --- | --- |
| GET | `/health` | Status, jumlah lowongan, backend semantik yang aktif |
| GET | `/meta` | Daftar level, lokasi, jenis pekerjaan, dan metode untuk mengisi filter |
| POST | `/search` | Pencarian: kueri bebas, metode, filter, skill pengguna, paginasi |
| GET | `/jobs`, `/jobs/{id}` | Daftar dan detail lowongan |
| POST | `/jobs/{id}/match` | Skor kecocokan satu lowongan terhadap skill pengguna |
| GET | `/skills` | Kamus skill dan alias |
| POST | `/extract-skills` | Ekstraksi skill dari teks (misalnya teks CV) |
| GET | `/admin/stats` | Statistik data dan indeks |
| GET | `/admin/evaluate` | Evaluasi semua metode dengan `qrels.csv` |
| POST, DELETE | `/admin/jobs`, `/admin/jobs/{id}` | Tambah dan hapus lowongan (indeks dibangun ulang) |

Contoh:

```bash
curl -X POST localhost:8000/search -H 'content-type: application/json' -d '{
  "query": "Saya menguasai Python dan SQL, cari kerja fresh graduate di bidang analisis data",
  "filters": {"location": "Jakarta"}, "limit": 5
}'
```

Respons memuat `understood` (skill, level, lokasi yang dibaca dari kueri) dan `results`, tiap hasil dengan
`match.score`, komponen `S R E L`, `missing`, `explanation`, serta peringkat BM25 dan semantik.

## Tes

```bash
pip install pytest httpx
python -m pytest -q
```

## Batasan versi ini

- Belum ada login pengguna. `/admin` hanya dilindungi kunci sederhana bila `TEPAT_ADMIN_KEY` diisi.
- Data berada di memori dan dibaca dari CSV saat start. Lowongan yang ditambah lewat admin hilang saat server mati.
  Langkah berikutnya adalah PostgreSQL (lihat rancangan tabel di PRD).
- Menambah atau menghapus lowongan membangun ulang seluruh indeks, cukup untuk ribuan lowongan.
- Dua pengguna yang mengakses bersamaan aman (indeks dikunci saat dibangun ulang), tetapi belum diuji beban.


## Database

Variabel `TEPAT_DATABASE_URL` (URL SQLAlchemy). Bawaan `sqlite:///backend/tepat.db`; contoh PostgreSQL:
`postgresql+psycopg://user:sandi@localhost:5432/tepat`; `memory` = tanpa database. `/health` menampilkan `database`.
Tes memakai SQLite sementara. Untuk menguji ke PostgreSQL: `TEST_DATABASE_URL=postgresql+psycopg://... pytest`
(tes menambah dan menghapus satu lowongan di tabel itu).

Kamus skill juga disimpan di tabel `skills` (diisi dari `dataset/skills.csv` saat kosong). Admin bisa menambah alias
lewat `POST /admin/skills/{nama}/aliases` dan skill baru lewat `POST /admin/skills`; keduanya membangun ulang indeks.
Skill atau alias yang bentrok dengan yang sudah ada ditolak (409). Skill tidak bisa dihapus atau diubah namanya dari API,
karena lowongan lama menyimpan nama skill sebagai teks.

Batasan: skema dibuat dengan `create_all` tanpa migrasi (Alembic bila skema mulai berubah), dan indeks pencarian
dibangun ulang seluruhnya setiap tambah atau hapus, cukup untuk ribuan lowongan. Dengan beberapa proses server
(`--workers`), perubahan di satu proses tidak terlihat di proses lain sampai dimulai ulang.


## Login admin

Endpoint `/admin/*` terkunci begitu ada minimal satu akun admin di database (atau `TEPAT_ADMIN_KEY` diisi).
**Selama belum ada akun atau kunci, admin terbuka untuk siapa saja. Cukup untuk belajar di komputer sendiri, jangan untuk server publik.**

```bash
python create_admin.py dary                         # sandi ditanya, minimal 8 karakter
# atau saat start pertama, bila tabel admins masih kosong:
TEPAT_ADMIN_USER=dary TEPAT_ADMIN_PASSWORD='...' uvicorn app.main:app
export TEPAT_SECRET='string-acak-panjang'           # kunci penandatangan token; tanpa ini token tidak berlaku lagi setelah restart
```

- `POST /auth/login` `{username, password}` mengembalikan token bertanda tangan HMAC yang berlaku 12 jam. Kirim sebagai
  `Authorization: Bearer <token>`. `GET /auth/me` memeriksa token.
- Sandi disimpan sebagai hash scrypt berbunga acak. Percobaan gagal dibatasi 5 kali per 5 menit per pengguna dan alamat klien.
- `X-Admin-Key` tetap berlaku bila `TEPAT_ADMIN_KEY` diisi (untuk skrip).

Batasan: token tidak bisa dicabut sebelum kedaluwarsa (tanpa daftar sesi), hanya ada satu peran admin, tidak ada fitur lupa sandi
(jalankan `create_admin.py` lagi untuk mengganti), pembatas percobaan hanya di memori satu proses, dan lalu lintas harus lewat HTTPS
saat dipasang di server sungguhan. Di mode `memory` login tidak tersedia.


## Kata "magang" dan kecocokan level

- `understand_query` hanya menganggap kueri sebagai pencarian magang bila "magang" tidak berupa riwayat. Frasa seperti
  "pernah magang", "pengalaman magang 3 bulan", atau "setelah magang" diabaikan. Kata "magang" itu tetap ikut dicari sebagai
  kata biasa oleh BM25, jadi hasil teratas masih bisa memuat lowongan magang.
- Komponen E (level) dan L (lokasi) dikalikan `min(1, R / GATE_R)` dengan `GATE_R = 40` (di `matching.py`). Level dan lokasi
  hanya berarti penuh bila bidang lowongan cocok. Nilai 40 adalah hipotesis untuk skala cosine LSA dan perlu diuji ulang
  bila backend semantik diganti ke SBERT. Evaluasi P@5, NDCG, dan lainnya tidak berubah karena memakai peringkat, bukan skor akhir.
- Antarmuka menampilkan chip **Hanya Magang** (atau jenis lain yang terbaca) yang menerapkan filter jenis dengan satu klik.
