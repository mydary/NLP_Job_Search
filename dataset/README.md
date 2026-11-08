# Dataset Tepat Karir (sintetis)

Semua data di folder ini dibuat oleh `generate_dataset.py` dengan seed tetap, jadi hasilnya selalu sama.
Perusahaan, lowongan, dan gaji adalah fiktif. Jangan dipakai sebagai informasi pasar kerja yang sebenarnya.

Jalankan ulang: `python3 generate_dataset.py` (hanya butuh Python 3, tanpa pustaka tambahan).

## Berkas

| Berkas | Isi |
| --- | --- |
| `jobs.csv` | 368 lowongan (360 asli + 8 posting ulang yang hampir kembar) |
| `skills.csv` | 56 skill baku, kategori, dan alias |
| `queries.csv` | 30 kueri uji (bahasa Indonesia, Inggris, dan daftar skill) |
| `qrels.csv` | Penilaian relevansi kueri-lowongan: 2 = sangat relevan, 1 = cukup relevan. Baris bernilai 0 tidak ditulis |

## Kolom `jobs.csv`

Sembilan kolom inti dari rancangan awal: `job_id`, `job_title`, `company`, `description`, `required_skills`,
`preferred_skills`, `experience_level`, `location`, `employment_type`.

Kolom tambahan: `salary_min` dan `salary_max` (juta rupiah per bulan, kosong pada sekitar 18% baris seperti di portal
sungguhan), `posted_at`, `deadline`, `source`, `family` (bidang, dipakai untuk evaluasi), dan `dup_of` (diisi
`job_id` asli bila baris itu posting ulang, dipakai untuk menguji deteksi duplikat).

Skill dipisah titik koma dan memakai nama baku dari `skills.csv`. Pada `description`, skill sengaja ditulis dengan
variasi ("MS Excel", "Postgre SQL", "pipeline data", "pemasaran digital") agar ekstraksi dan normalisasi skill
benar-benar teruji.

## Sifat data yang disengaja

- Sekitar 28% deskripsi berbahasa Inggris, sisanya bahasa Indonesia.
- Sekitar 31% lowongan tidak punya skill nilai tambah, sebagian deskripsi sangat pendek.
- Level pengalaman: Internship, Entry Level, Junior, Mid-level, Senior.
- 16 bidang: data, bi, ml, backend, frontend, mobile, devops, security, design, marketing, content, finance, admin, hr,
  sales, pm. Banyak peran beririsan (misalnya Data Analyst dan BI Analyst) agar pencarian semantik punya tantangan.

## Catatan evaluasi

`qrels.csv` dibuat dari aturan: bidang lowongan cocok dengan bidang utama kueri (nilai 2), cocok dengan bidang
sekunder (nilai 1), lalu diturunkan bila level atau lokasi yang diminta kueri tidak sesuai. Ini penilaian otomatis
dari data sintetis, bukan dari penilai manusia. Untuk laporan penelitian, ganti atau validasi dengan penilaian manual.
