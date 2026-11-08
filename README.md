# Tepat Karir: mesin pencarian lowongan berbasis NLP

Proyek belajar Information Retrieval dan NLP untuk bahasa Indonesia. Pengguna menulis kemampuan atau pekerjaan
yang dicari dengan kalimat biasa, lalu sistem mengembalikan lowongan berperingkat beserta skor kecocokan,
skill yang belum dimiliki, dan alasannya.

## Isi

| Folder | Isi |
| --- | --- |
| `dataset/` | Data sintetis: `jobs.csv` (368 lowongan), `skills.csv`, `queries.csv`, `qrels.csv`, dan generatornya |
| `nlp_engine/` | Kode inti: `preprocessing.py`, `skills.py`, `retrieval.py` (indeks terbalik, TF-IDF, BM25, semantik, RRF), `matching.py`, `evaluation.py` |
| `notebooks/` | Lima notebook pembelajaran (01 sampai 05), sudah dijalankan sehingga hasilnya terlihat |
| `backend/` | API FastAPI di atas `nlp_engine`, lengkap dengan tes |
| `index.html` | Antarmuka web satu berkas. Memakai API bila server menyala, bila tidak memakai mesin di browser (41 lowongan demo) |

## Cara menjalankan

```bash
pip install -r requirements.txt
cd notebooks
jupyter lab
```

Jalankan notebook berurutan:

0. `01_eda_dataset.ipynb`: bentuk, nilai kosong, sebaran, skill, dan duplikat pada dataset.
1. `02_preprocessing_skill_extraction.ipynb`: praproses, stopword, stemming, ekstraksi skill, akurasi ekstraksi.
2. `03_inverted_index_bm25.ipynb`: indeks terbalik, Boolean search, TF-IDF, BM25, metrik evaluasi.
3. `04_semantic_search.ipynb`: embedding dan cosine similarity, masalah vocabulary mismatch.
4. `05_hybrid_and_scoring.ipynb`: RRF, skor kecocokan, skill gap, perbandingan E1 sampai E5.

Setiap notebook berakhir dengan latihan.

## Menjalankan API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload     # lalu buka http://127.0.0.1:8000/docs
```

Rincian endpoint dan batasannya ada di `backend/README.md`.

### Database (PostgreSQL)

Lowongan disimpan di tabel `jobs` dan kamus skill di tabel `skills` (modul `nlp_engine/store.py`, SQLAlchemy). Saat tabel masih kosong, ia diisi dari
`dataset/jobs.csv`; setelah itu lowongan yang ditambah atau dihapus lewat admin tetap ada walau server dimulai ulang.
Tanpa pengaturan apa pun API memakai SQLite (`backend/tepat.db`). Untuk PostgreSQL:

```bash
createdb tepat
export TEPAT_DATABASE_URL='postgresql+psycopg://USER:SANDI@localhost:5432/tepat'
uvicorn app.main:app
```

`TEPAT_DATABASE_URL=memory` mematikan database (data kembali ke CSV setiap start). Indeks BM25 dan semantik tetap dibangun
di memori dari isi tabel, dan dibangun ulang setiap ada perubahan data.

## Menyambungkan `index.html` ke API

1. Jalankan API seperti di atas.
2. Buka `index.html` dari berkas lokal (klik dua kali) atau lewat `python3 -m http.server`.
3. Klik tombol **Mesin** di pojok kanan atas. Alamat bawaan `http://127.0.0.1:8000`; isi kunci admin bila `TEPAT_ADMIN_KEY` diatur, lalu tekan **Hubungkan**.

Isi nama pengguna dan sandi admin di panel yang sama bila server sudah punya akun admin (lihat `backend/README.md`, bagian Login admin).

Setelah terhubung, pencarian, detail, rekomendasi dasbor, dan tab admin (ringkasan, lowongan, evaluasi) memakai data 368 lowongan dari server. Bila server mati di tengah jalan, antarmuka kembali ke mesin browser. Halaman Artifact yang dipublikasikan tidak bisa menghubungi server di komputermu (dibatasi CSP), jadi mode API hanya jalan dari berkas yang diunduh.

## Mengaktifkan SBERT

Secara bawaan pencarian semantik memakai `backend="auto"`: SBERT bila `sentence-transformers` terpasang dan model
bisa diunduh, bila tidak memakai LSA (TF-IDF + SVD). Untuk SBERT:

```bash
pip install sentence-transformers
```

Notebook 04 dan 05 menampilkan backend mana yang dipakai. Hasil di notebook yang tersimpan dihitung dengan LSA,
karena model SBERT tidak bisa diunduh di lingkungan tempat notebook itu dijalankan.

## Catatan penting

- Semua data sintetis. Relevansi di `qrels.csv` dibuat otomatis dari label bidang, bukan oleh penilai manusia.
- Dengan 30 kueri, selisih kecil antar metode belum bermakna. Lihat analisis per kueri di notebook 05.
- Recall@10 dilaporkan sebagai recall terbatas (hit dibagi min(10, jumlah relevan)), karena satu kueri bisa punya
  puluhan lowongan relevan.
- Skor kecocokan adalah perkiraan kesesuaian berdasarkan kriteria sistem, bukan peluang diterima kerja.
