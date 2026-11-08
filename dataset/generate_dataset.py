#!/usr/bin/env python3
"""Generator dataset dummy Tepat Karir (seed tetap, hasil selalu sama).

Keluaran (folder ini):
  jobs.csv     lowongan sintetis
  skills.csv   kamus skill + alias
  queries.csv  kueri uji
  qrels.csv    penilaian relevansi kueri-lowongan (0-2, hanya baris > 0)
"""
import csv, random, datetime as dt, os, re

RNG = random.Random(20261107)
OUT = os.path.dirname(os.path.abspath(__file__))
N_JOBS = 360

LEVEL_LABEL = ['Internship', 'Entry Level', 'Junior', 'Mid-level', 'Senior']
LEVEL_MULT = [0.45, 1.0, 1.35, 1.9, 2.8]
LOCS = [('Jakarta', 30), ('Bandung', 10), ('Surabaya', 9), ('Yogyakarta', 7), ('Tangerang', 8),
        ('Bekasi', 5), ('Serang', 5), ('Semarang', 5), ('Denpasar', 3), ('Remote', 12)]
LOC_MULT = {'Jakarta': 1.0, 'Bandung': .85, 'Surabaya': .9, 'Yogyakarta': .75, 'Tangerang': .95, 'Bekasi': .92,
            'Serang': .8, 'Semarang': .82, 'Denpasar': .88, 'Remote': 1.0}

# ---------- kamus skill: nama baku -> (kategori, variasi tulisan) ----------
SK = {
 'Python': ('Pemrograman', ['Python', 'Python', 'python', 'Python 3'], ['py', 'python3']),
 'SQL': ('Database', ['SQL', 'SQL', 'query SQL'], ['sql server', 'structured query language']),
 'Microsoft Excel': ('Analisis Data', ['Excel', 'MS Excel', 'Microsoft Excel', 'spreadsheet'], ['excel', 'ms excel', 'spreadsheet', 'google sheets']),
 'Power BI': ('Visualisasi Data', ['Power BI', 'PowerBI', 'Power BI Desktop'], ['powerbi', 'power bi desktop']),
 'Tableau': ('Visualisasi Data', ['Tableau', 'Looker Studio'], ['looker studio', 'data studio']),
 'Pandas': ('Analisis Data', ['Pandas', 'Pandas dan NumPy'], ['numpy', 'dataframe']),
 'Machine Learning': ('Machine Learning', ['machine learning', 'Machine Learning', 'ML'], ['ml', 'deep learning', 'scikit-learn', 'pembelajaran mesin']),
 'Statistik': ('Analisis Data', ['statistik', 'statistika', 'SPSS'], ['statistics', 'statistika', 'spss']),
 'NLP': ('Machine Learning', ['NLP', 'natural language processing', 'pemrosesan bahasa alami'], ['natural language processing', 'text mining']),
 'Analisis Data': ('Analisis Data', ['analisis data', 'data analysis', 'analisa data'], ['analis data', 'data analytics', 'mengolah data', 'olah data']),
 'Visualisasi Data': ('Visualisasi Data', ['visualisasi data', 'dashboard', 'data visualization'], ['visualisasi', 'dashboard', 'grafik']),
 'ETL': ('Database', ['ETL', 'pipeline data'], ['data pipeline', 'pipeline data']),
 'PostgreSQL': ('Database', ['PostgreSQL', 'Postgre SQL', 'Postgres'], ['postgre sql', 'postgres']),
 'MySQL': ('Database', ['MySQL', 'MariaDB'], ['mariadb']),
 'Django': ('Pemrograman', ['Django'], []),
 'FastAPI': ('Pemrograman', ['FastAPI', 'Fast API'], ['fast api']),
 'PHP': ('Pemrograman', ['PHP'], []),
 'Laravel': ('Pemrograman', ['Laravel'], []),
 'JavaScript': ('Pemrograman', ['JavaScript', 'JS'], ['js']),
 'TypeScript': ('Pemrograman', ['TypeScript', 'TS'], ['ts']),
 'Node.js': ('Pemrograman', ['Node.js', 'NodeJS'], ['nodejs', 'node js', 'express.js']),
 'React': ('Pemrograman', ['React', 'ReactJS', 'React.js'], ['reactjs', 'react.js', 'next.js']),
 'HTML/CSS': ('Pemrograman', ['HTML dan CSS', 'HTML5 dan CSS3', 'HTML/CSS'], ['html', 'css', 'html5', 'css3', 'tailwind']),
 'REST API': ('Pemrograman', ['REST API', 'RESTful API', 'API'], ['api', 'restful', 'rest', 'web service']),
 'Git': ('Alat Kerja', ['Git', 'GitHub', 'Git/GitHub'], ['github', 'gitlab', 'version control']),
 'Docker': ('Infrastruktur', ['Docker', 'container'], ['container', 'kontainer']),
 'Linux': ('Infrastruktur', ['Linux', 'Ubuntu'], ['ubuntu', 'bash', 'shell']),
 'AWS': ('Infrastruktur', ['AWS', 'cloud (AWS/GCP)'], ['amazon web services', 'cloud', 'gcp', 'azure']),
 'CI/CD': ('Infrastruktur', ['CI/CD', 'GitHub Actions'], ['ci cd', 'github actions', 'jenkins']),
 'Flutter': ('Pemrograman', ['Flutter', 'Flutter (Dart)'], ['dart']),
 'Android': ('Pemrograman', ['Android', 'Kotlin'], ['kotlin', 'android studio']),
 'Jaringan Komputer': ('Infrastruktur', ['jaringan komputer', 'networking', 'Mikrotik'], ['networking', 'jaringan', 'cisco', 'mikrotik', 'tcp/ip']),
 'Keamanan Siber': ('Keamanan', ['keamanan siber', 'cybersecurity', 'keamanan informasi'], ['cybersecurity', 'cyber security', 'pentest', 'penetration testing']),
 'Figma': ('Desain', ['Figma'], ['adobe xd', 'sketch']),
 'UI/UX Design': ('Desain', ['UI/UX', 'desain UI/UX', 'UX design'], ['ui/ux', 'ui ux', 'user experience', 'user interface']),
 'Riset Pengguna': ('Desain', ['user research', 'riset pengguna'], ['user research', 'usability testing']),
 'Adobe Photoshop': ('Desain', ['Photoshop', 'Adobe Photoshop', 'Canva'], ['photoshop', 'illustrator', 'canva', 'coreldraw']),
 'Desain Grafis': ('Desain', ['desain grafis', 'graphic design'], ['graphic design', 'desain poster']),
 'Video Editing': ('Konten', ['video editing', 'Premiere Pro', 'CapCut'], ['edit video', 'premiere', 'capcut', 'after effects']),
 'Digital Marketing': ('Pemasaran', ['digital marketing', 'pemasaran digital'], ['pemasaran digital', 'meta ads', 'google ads', 'iklan online']),
 'SEO': ('Pemasaran', ['SEO', 'search engine optimization'], ['search engine optimization']),
 'Google Analytics': ('Pemasaran', ['Google Analytics', 'GA4'], ['ga4']),
 'Social Media': ('Pemasaran', ['media sosial', 'social media'], ['sosial media', 'instagram', 'tiktok']),
 'Copywriting': ('Konten', ['copywriting', 'menulis copy'], ['copywriter', 'caption']),
 'Content Writing': ('Konten', ['content writing', 'penulisan konten', 'menulis artikel'], ['content writer', 'penulis konten']),
 'Akuntansi': ('Keuangan', ['akuntansi', 'pembukuan', 'Accurate/Zahir'], ['accounting', 'pembukuan', 'laporan keuangan', 'zahir', 'accurate']),
 'Pajak': ('Keuangan', ['perpajakan', 'pajak', 'SPT'], ['perpajakan', 'taxation', 'spt', 'pph']),
 'Microsoft Office': ('Alat Kerja', ['Microsoft Office', 'MS Word dan PowerPoint'], ['ms office', 'ms word', 'powerpoint']),
 'Administrasi': ('Administrasi', ['administrasi perkantoran', 'pengarsipan'], ['pengarsipan', 'data entry', 'surat menyurat']),
 'Rekrutmen': ('SDM', ['rekrutmen', 'recruitment', 'talent acquisition'], ['recruitment', 'recruiting', 'merekrut', 'screening cv']),
 'Customer Service': ('Layanan', ['layanan pelanggan', 'customer service'], ['layanan pelanggan', 'cs', 'customer support']),
 'Penjualan': ('Layanan', ['penjualan', 'sales'], ['sales', 'menjual', 'target penjualan']),
 'Negosiasi': ('Layanan', ['negosiasi'], ['negotiation', 'bernegosiasi']),
 'Komunikasi': ('Soft Skill', ['komunikasi', 'public speaking'], ['communication', 'public speaking', 'presentasi']),
 'Manajemen Proyek': ('Manajemen', ['manajemen proyek', 'project management'], ['project management', 'pmp']),
 'Agile': ('Manajemen', ['Agile', 'Scrum'], ['scrum', 'kanban', 'sprint']),
}

# ---------- perusahaan fiktif ----------
TECH = {'tech', 'fintech', 'ecom', 'logistik', 'edu', 'media'}
COMPANIES = [
 ('PT Nusantara Analitika', {'tech'}), ('Arunika AI Labs', {'tech'}), ('Bahasa Lab', {'tech', 'edu'}),
 ('Awan Biru Cloud', {'tech'}), ('Benteng Siber', {'tech'}), ('Teknologi Kota Pintar', {'tech'}),
 ('Studio Piksel', {'tech', 'media'}), ('Lensa Produk', {'tech', 'media'}), ('Aplikasi Rakyat', {'tech'}),
 ('Rumah Digital Nusa', {'tech', 'ecom'}), ('Dagang Cepat', {'ecom'}), ('Gerai Online Indonesia', {'ecom'}),
 ('Kopi Lintas Digital', {'ecom', 'media'}), ('PT Sentosa Finansial Teknologi', {'fintech'}),
 ('Dompet Bersama', {'fintech'}), ('Koperasi Digital Maju', {'fintech'}), ('Mitra Logistik Prima', {'logistik'}),
 ('Kirim Kilat Nusantara', {'logistik'}), ('Edukasi Nusantara', {'edu'}), ('Sekolah Pintar Indonesia', {'edu'}),
 ('Media Nusa Kata', {'media'}), ('Cerita Visual', {'media'}), ('Kreasi Cetak Mandiri', {'media', 'manufaktur'}),
 ('Survei Cendekia', {'konsultan'}), ('Konsultan Pajak Tertib', {'konsultan'}), ('Talenta Karya', {'konsultan'}),
 ('Sinar Perkasa', {'manufaktur', 'retail'}), ('Mitra Solusi Teknologi', {'tech', 'konsultan'}),
 ('Jaringan Sentra', {'tech'}), ('Warung Pintar Group', {'retail', 'ecom'}), ('Toko Sejahtera', {'retail'}),
 ('Pabrik Sumber Makmur', {'manufaktur'}), ('Karya Baja Utama', {'manufaktur'}), ('Rumah Sakit Harapan Bersama', {'umum'}),
 ('Hotel Pesisir Indah', {'umum'}), ('Agrotani Digital', {'tech', 'umum'}), ('Bank Mitra Rakyat', {'fintech', 'umum'}),
 ('Asuransi Sentra Jiwa', {'fintech', 'umum'}), ('Properti Cakrawala', {'umum', 'retail'}),
 ('Wisata Nusa Tour', {'umum'}), ('Ritel Segar Mart', {'retail'}), ('Studio Kreasi Lokal', {'media'}),
 ('Konstruksi Bangun Jaya', {'manufaktur', 'umum'}), ('Energi Hijau Nusantara', {'manufaktur', 'umum'}),
]

# ---------- peran ----------
ROLES = []
def R(key, fam, base, levels, req, opt, extra, resp, resp_en, dept, major, sal, tech=True):
    ROLES.append(dict(key=key, fam=fam, base=base, levels=levels, req=req, opt=opt, extra=extra, resp=resp,
                      resp_en=resp_en, dept=dept, major=major, sal=sal, tech=tech))

R('da', 'data', 'Data Analyst', [0, 1, 1, 2, 2, 3], ['SQL', 'Microsoft Excel'], ['Python', 'Pandas', 'Power BI', 'Visualisasi Data', 'Analisis Data', 'Statistik'], ['Tableau'],
  ['mengolah dataset penjualan dan membersihkan data yang tidak konsisten', 'menyusun laporan analisis mingguan untuk tim bisnis', 'menulis query untuk menarik data dari database perusahaan', 'mengidentifikasi tren dan pola dari data operasional', 'menyajikan temuan analisis kepada pemangku kepentingan'],
  ['analyze business data and turn it into clear recommendations', 'build and maintain recurring reports for the business team'], 'Data', 'Statistika, Matematika, Sistem Informasi, atau Teknik Informatika', 7)
R('de', 'data', 'Data Engineer', [2, 3, 3, 4], ['Python', 'SQL', 'ETL'], ['PostgreSQL', 'Docker', 'AWS', 'Git'], ['Linux', 'CI/CD'],
  ['membangun dan merawat pipeline data harian dari berbagai sumber', 'memastikan kualitas dan ketersediaan data untuk tim analis', 'merancang skema tabel di gudang data', 'memantau pekerjaan ETL dan menangani kegagalan'],
  ['design and operate data pipelines at scale', 'work with analysts to make reliable datasets available'], 'Data Platform', 'Teknik Informatika atau Ilmu Komputer', 13)
R('ra', 'data', 'Analis Riset Pasar', [1, 2, 3], ['Microsoft Excel', 'Statistik', 'Komunikasi'], ['Visualisasi Data', 'Analisis Data', 'Microsoft Office'], ['SQL'],
  ['mengolah data survei dan menganalisis perilaku konsumen', 'menulis laporan riset untuk klien', 'merancang kuesioner dan mengatur pengumpulan data lapangan', 'mempresentasikan hasil riset kepada klien'],
  ['analyze survey results and write research reports for clients'], 'Riset', 'Statistika, Manajemen, atau Psikologi', 6)
R('bi', 'bi', 'Business Intelligence Analyst', [1, 2, 3, 3], ['SQL', 'Power BI', 'Microsoft Excel'], ['Tableau', 'Python', 'Visualisasi Data', 'ETL'], ['Analisis Data'],
  ['merancang dashboard dan laporan KPI untuk manajemen', 'memproses data transaksi menjadi informasi yang siap dibaca', 'menyajikan business insight dalam rapat bulanan', 'bekerja sama dengan tim data untuk menyiapkan model data pelaporan'],
  ['design dashboards and KPI reports for management', 'translate business questions into data models and reports'], 'Business Intelligence', 'Sistem Informasi, Statistika, atau Manajemen', 9)
R('ba', 'bi', 'Business Analyst', [1, 2, 3], ['Microsoft Excel', 'SQL', 'Komunikasi'], ['Power BI', 'Analisis Data', 'Manajemen Proyek'], ['Agile'],
  ['menggali kebutuhan bisnis dari tiap divisi', 'menganalisis proses operasional dan mencari titik perbaikan', 'menyusun rekomendasi berbasis data untuk pemangku kepentingan', 'menulis dokumen kebutuhan bisnis untuk tim teknologi'],
  ['gather business requirements and recommend process improvements'], 'Strategi Bisnis', 'Manajemen, Sistem Informasi, atau Teknik Industri', 8)
R('rep', 'bi', 'Reporting Analyst', [1, 2], ['Microsoft Excel', 'SQL'], ['Power BI', 'Visualisasi Data'], ['Microsoft Office'],
  ['menyusun laporan harian dan bulanan untuk divisi operasional', 'memeriksa kesesuaian angka antar sistem', 'merapikan template laporan dan mengotomatiskannya', 'menjawab permintaan data dari tim lain'],
  ['prepare daily and monthly operational reports'], 'Operasional', 'Akuntansi, Manajemen, atau Sistem Informasi', 6.5)
R('ds', 'ml', 'Data Scientist', [0, 1, 3, 3, 4], ['Python', 'Machine Learning', 'Statistik', 'SQL'], ['Pandas', 'Docker', 'NLP', 'Git'], ['Tableau'],
  ['membangun model prediksi churn dan rekomendasi produk', 'mengevaluasi performa model dan memperbaikinya', 'bekerja dengan tim produk agar model bisa dipakai di aplikasi', 'melakukan eksplorasi data dan rekayasa fitur'],
  ['build and evaluate predictive models for product teams', 'run experiments and communicate results to non-technical stakeholders'], 'Data Science', 'Statistika, Matematika, atau Ilmu Komputer', 11)
R('mle', 'ml', 'Machine Learning Engineer', [2, 3, 4], ['Python', 'Machine Learning', 'Docker'], ['AWS', 'FastAPI', 'Git', 'CI/CD'], ['PostgreSQL'],
  ['membawa model dari tahap riset ke layanan produksi', 'membangun API untuk menyajikan model', 'memantau performa model setelah dirilis', 'mengotomatiskan pelatihan ulang model'],
  ['deploy and monitor machine learning models in production'], 'Machine Learning', 'Ilmu Komputer atau Teknik Informatika', 15)
R('nlp', 'ml', 'NLP Engineer', [2, 3, 4], ['Python', 'Machine Learning', 'NLP'], ['FastAPI', 'Docker', 'Pandas'], ['Git'],
  ['membangun layanan NLP berbahasa Indonesia seperti klasifikasi teks dan pencarian semantik', 'menganalisis sentimen dari media sosial dan ulasan pelanggan', 'menyiapkan dan memberi label pada korpus teks', 'mengevaluasi model bahasa dengan metrik yang sesuai'],
  ['build Indonesian language NLP services such as text classification and semantic search'], 'AI Bahasa', 'Ilmu Komputer, Linguistik Komputasi, atau Teknik Informatika', 14)
R('bed', 'backend', 'Backend Developer', [0, 1, 2, 2, 3], ['Python', 'Django', 'PostgreSQL', 'Git'], ['Docker', 'REST API', 'FastAPI'], ['Linux'],
  ['mengembangkan API untuk aplikasi layanan publik', 'merancang tabel database dan menulis query yang efisien', 'menulis pengujian otomatis dan memperbaiki bug', 'melakukan review kode rekan satu tim'],
  ['build and maintain REST APIs for web and mobile clients'], 'Engineering', 'Teknik Informatika atau Sistem Informasi', 8.5)
R('bel', 'backend', 'Backend Developer Laravel', [1, 2, 3], ['PHP', 'Laravel', 'MySQL', 'Git'], ['REST API', 'Docker'], ['JavaScript'],
  ['membangun fitur backend untuk platform pemesanan', 'mengintegrasikan layanan pembayaran dan notifikasi', 'merawat dan merapikan kode lama', 'membuat dokumentasi API untuk tim frontend'],
  ['develop backend features for an online booking platform'], 'Engineering', 'Teknik Informatika atau Sistem Informasi', 8)
R('ben', 'backend', 'Node.js Developer', [2, 3, 4], ['JavaScript', 'Node.js', 'REST API', 'PostgreSQL'], ['Docker', 'AWS', 'TypeScript'], ['Git'],
  ['merancang layanan backend berskala besar untuk toko online', 'menjaga performa dan keamanan API', 'mereview kode dan membimbing developer junior', 'menangani insiden produksi bersama tim DevOps'],
  ['design scalable backend services for an e-commerce platform'], 'Engineering', 'Teknik Informatika atau Ilmu Komputer', 13)
R('fe', 'frontend', 'Frontend Developer', [0, 1, 2, 2, 3], ['JavaScript', 'React', 'HTML/CSS', 'Git'], ['TypeScript', 'Figma', 'REST API'], [],
  ['membangun antarmuka web responsif dari desain Figma', 'menjaga konsistensi komponen antarmuka', 'memperbaiki performa dan aksesibilitas halaman', 'menghubungkan antarmuka dengan API backend'],
  ['build responsive web interfaces from design files', 'collaborate with designers to keep components consistent'], 'Engineering', 'Teknik Informatika atau Sistem Informasi', 8.5)
R('wd', 'frontend', 'Web Developer', [1, 2], ['HTML/CSS', 'JavaScript'], ['React', 'Git', 'PHP'], ['MySQL'],
  ['membuat dan merawat website perusahaan untuk klien', 'menyesuaikan tampilan di berbagai ukuran layar', 'memperbarui konten dan memperbaiki bug', 'mengatur hosting dan nama domain'],
  ['build and maintain company websites for clients'], 'Proyek Web', 'Teknik Informatika, Sistem Informasi, atau DKV', 6)
R('flu', 'mobile', 'Flutter Developer', [0, 1, 2, 3], ['Flutter', 'Git'], ['REST API', 'Figma'], ['Android'],
  ['mengembangkan aplikasi mobile Android dan iOS dengan Flutter', 'menghubungkan aplikasi dengan API', 'merilis aplikasi ke Play Store dan App Store', 'memperbaiki bug dari laporan pengguna'],
  ['build cross-platform mobile apps with Flutter'], 'Mobile', 'Teknik Informatika atau Sistem Informasi', 8.5)
R('and', 'mobile', 'Android Developer', [0, 1, 2, 3], ['Android', 'Git'], ['REST API', 'Flutter'], [],
  ['membangun fitur aplikasi Android untuk platform belajar', 'menulis kode Kotlin yang mudah dirawat', 'melakukan pengujian dan memperbaiki crash', 'bekerja sama dengan desainer untuk antarmuka aplikasi'],
  ['develop features for a native Android app'], 'Mobile', 'Teknik Informatika atau Sistem Informasi', 8.5)
R('devops', 'devops', 'DevOps Engineer', [2, 3, 3, 4], ['Docker', 'Linux', 'AWS', 'CI/CD'], ['Git', 'Jaringan Komputer'], [],
  ['mengelola server dan deployment aplikasi di cloud', 'membangun pipeline CI/CD untuk tim engineering', 'memantau ketersediaan layanan dan menangani insiden', 'mengotomatiskan penyiapan infrastruktur'],
  ['manage cloud infrastructure and CI/CD pipelines'], 'Infrastruktur', 'Teknik Informatika atau Teknik Komputer', 14)
R('net', 'devops', 'Network Administrator', [1, 2, 3], ['Jaringan Komputer', 'Linux'], ['Keamanan Siber'], ['Microsoft Office'],
  ['merawat jaringan kantor dan server', 'menangani gangguan koneksi dan perangkat', 'memantau lalu lintas jaringan', 'mengelola akses pengguna dan perangkat Wi-Fi'],
  ['maintain office networks and servers'], 'IT Infrastruktur', 'Teknik Informatika, Teknik Komputer, atau Telekomunikasi', 7.5)
R('its', 'devops', 'IT Support', [1, 2], ['Microsoft Office', 'Jaringan Komputer', 'Komunikasi'], ['Linux'], [],
  ['membantu pengguna kantor menyelesaikan masalah komputer dan aplikasi', 'mencatat dan menindaklanjuti tiket bantuan', 'menyiapkan perangkat untuk karyawan baru', 'merawat printer dan perangkat jaringan'],
  ['provide first-line IT support to office users'], 'IT', 'Teknik Informatika atau Sistem Informasi', 5)
R('sec', 'security', 'Security Analyst', [1, 2, 3, 4], ['Keamanan Siber', 'Linux', 'Jaringan Komputer'], ['Python', 'Docker'], [],
  ['memantau peringatan keamanan dan menganalisis insiden', 'membantu menutup celah keamanan pada sistem', 'menyusun laporan temuan dan rekomendasi perbaikan', 'melakukan pengujian kerentanan secara berkala'],
  ['monitor security alerts and investigate incidents'], 'Keamanan Informasi', 'Teknik Informatika atau Keamanan Siber', 10)
R('ux', 'design', 'UI/UX Designer', [0, 1, 2, 3], ['Figma', 'UI/UX Design'], ['Riset Pengguna', 'Adobe Photoshop'], [],
  ['merancang alur dan tampilan aplikasi', 'membuat prototipe dan menguji desain bersama pengguna', 'menyerahkan spesifikasi desain kepada developer', 'menjaga konsistensi sistem desain produk'],
  ['design user flows and interfaces for web and mobile products', 'run usability tests and iterate on prototypes'], 'Desain Produk', 'Desain Komunikasi Visual, Teknik Informatika, atau Psikologi', 8)
R('gd', 'design', 'Graphic Designer', [1, 2, 3], ['Adobe Photoshop', 'Desain Grafis'], ['Video Editing', 'Figma'], [],
  ['menyiapkan desain brosur, spanduk, dan materi promosi', 'menyesuaikan desain dengan panduan merek klien', 'menyiapkan berkas untuk cetak dan untuk media digital', 'membuat ilustrasi sederhana untuk konten'],
  ['create marketing visuals for print and digital channels'], 'Kreatif', 'Desain Komunikasi Visual atau Desain Grafis', 6, False)
R('dm', 'marketing', 'Digital Marketing Specialist', [1, 2, 3], ['Digital Marketing', 'SEO', 'Google Analytics'], ['Social Media', 'Copywriting'], [],
  ['menjalankan kampanye iklan online di berbagai platform', 'mengoptimalkan konten agar mudah ditemukan di mesin pencari', 'melaporkan hasil kampanye setiap minggu', 'mengatur anggaran iklan dan menguji materi iklan'],
  ['run paid campaigns and report weekly performance'], 'Pemasaran', 'Manajemen, Komunikasi, atau Ilmu Pemasaran', 7.5, False)
R('smx', 'marketing', 'Social Media Specialist', [0, 1, 2], ['Social Media', 'Copywriting'], ['Desain Grafis', 'Video Editing', 'Google Analytics'], [],
  ['mengelola akun media sosial brand', 'menulis caption dan menjadwalkan unggahan', 'memantau interaksi audiens dan menjawab komentar', 'berkoordinasi dengan tim kreatif untuk materi konten'],
  ['manage brand social accounts and plan the content calendar'], 'Konten Sosial', 'Komunikasi, Desain Komunikasi Visual, atau Manajemen', 5.5, False)
R('seo', 'marketing', 'SEO Specialist', [2, 3], ['SEO', 'Google Analytics', 'Content Writing'], ['Digital Marketing'], [],
  ['menyusun strategi kata kunci', 'memperbaiki struktur situs agar mudah ditelusuri', 'memantau peringkat pencarian organik', 'berkoordinasi dengan penulis untuk konten yang sesuai kata kunci'],
  ['plan keyword strategy and monitor organic search ranking'], 'Pertumbuhan', 'Komunikasi, Manajemen, atau Teknik Informatika', 9, False)
R('cw', 'content', 'Content Writer', [0, 1, 2], ['Content Writing', 'SEO'], ['Copywriting', 'Social Media'], [],
  ['menulis artikel blog dan naskah konten edukatif', 'melakukan riset topik dan mengumpulkan sumber', 'menyunting tulisan rekan tim', 'menyesuaikan gaya bahasa dengan panduan merek'],
  ['write articles and scripts, and edit content for tone and accuracy'], 'Konten', 'Sastra, Komunikasi, Jurnalistik, atau Bahasa', 5, False)
R('ve', 'content', 'Video Editor', [1, 2, 2], ['Video Editing'], ['Adobe Photoshop', 'Desain Grafis'], [],
  ['menyunting video promosi dan konten media sosial', 'menambahkan teks animasi dan musik latar', 'menyesuaikan format video untuk tiap platform', 'mengelola arsip bahan video'],
  ['edit promotional videos and short-form social content'], 'Produksi Konten', 'Desain Komunikasi Visual, Film, atau Multimedia', 6.5, False)
R('acc', 'finance', 'Staf Akuntansi', [1, 2, 3], ['Akuntansi', 'Microsoft Excel'], ['Pajak', 'Microsoft Office'], ['SQL'],
  ['mencatat transaksi harian dan menyusun laporan keuangan bulanan', 'merekonsiliasi rekening bank', 'menyiapkan dokumen pendukung audit', 'memeriksa kelengkapan bukti transaksi'],
  ['record daily transactions and prepare monthly financial statements'], 'Keuangan', 'Akuntansi atau Manajemen Keuangan', 5.5, False)
R('tax', 'finance', 'Tax Officer', [1, 2, 3], ['Pajak', 'Akuntansi', 'Microsoft Excel'], [], [],
  ['menghitung dan melaporkan pajak perusahaan dan klien', 'menyiapkan dokumen pendukung pelaporan SPT', 'mendampingi proses pemeriksaan pajak', 'memantau perubahan peraturan perpajakan'],
  ['prepare and file corporate tax reports'], 'Perpajakan', 'Akuntansi atau Perpajakan', 6.5, False)
R('fin', 'finance', 'Finance Intern', [0], ['Microsoft Excel', 'Akuntansi'], [], [],
  ['membantu input data keuangan', 'menyusun rekap pengeluaran bulanan', 'menyiapkan bahan laporan untuk tim keuangan', 'mengarsipkan dokumen transaksi'],
  ['support the finance team with data entry and monthly reports'], 'Keuangan', 'Akuntansi atau Manajemen', 3, False)
R('adm', 'admin', 'Staf Administrasi', [1, 2], ['Microsoft Office', 'Administrasi', 'Komunikasi'], [], [],
  ['mengelola arsip dan dokumen kantor', 'menyusun surat menyurat', 'mengatur jadwal pertemuan pimpinan', 'menyiapkan kebutuhan rapat dan perjalanan dinas'],
  ['manage office documents, correspondence and schedules'], 'Umum', 'semua jurusan', 4.5, False)
R('det', 'admin', 'Admin Data Entry', [1], ['Microsoft Excel', 'Administrasi'], [], [],
  ['memasukkan data pesanan ke spreadsheet', 'memeriksa kesesuaian data dengan dokumen asli', 'merapikan data ganda dan data yang salah ketik', 'membuat rekap harian untuk atasan'],
  ['enter and verify order data in spreadsheets'], 'Operasional', 'semua jurusan', 3.8, False)
R('hr', 'hr', 'HR Recruiter', [0, 1, 2, 3], ['Rekrutmen', 'Komunikasi'], ['Microsoft Office'], [],
  ['memasang iklan lowongan dan menyaring CV', 'menjadwalkan dan melakukan wawancara awal', 'mengurus proses onboarding karyawan baru', 'memelihara basis data kandidat'],
  ['source and screen candidates, and coordinate interviews'], 'SDM', 'Psikologi, Manajemen, atau Hukum', 5.8, False)
R('hrg', 'hr', 'HR Generalist', [2, 3], ['Komunikasi', 'Microsoft Office', 'Administrasi'], ['Rekrutmen'], [],
  ['mengelola administrasi kepegawaian dan absensi', 'menyiapkan data penggajian setiap bulan', 'menangani pertanyaan karyawan seputar kebijakan', 'membantu penyusunan program pelatihan'],
  ['handle employee administration, payroll data and policy questions'], 'SDM', 'Psikologi, Manajemen, atau Hukum', 7, False)
R('cs', 'sales', 'Customer Service Officer', [1, 2], ['Customer Service', 'Komunikasi'], [], ['Microsoft Office'],
  ['melayani pertanyaan dan keluhan pelanggan lewat chat dan telepon', 'mencatat kasus dan menindaklanjuti sampai selesai', 'berkoordinasi dengan tim teknis untuk kendala pelanggan', 'menjaga standar kualitas layanan'],
  ['handle customer questions and complaints via chat and phone'], 'Layanan Pelanggan', 'semua jurusan', 4.8, False)
R('se', 'sales', 'Sales Executive', [1, 2, 3], ['Penjualan', 'Negosiasi', 'Komunikasi'], [], [],
  ['menemui calon klien dan menawarkan produk', 'bernegosiasi harga dan menutup penjualan', 'mengejar target penjualan bulanan', 'memelihara hubungan dengan pelanggan lama'],
  ['meet prospects, negotiate deals and hit monthly sales targets'], 'Penjualan', 'semua jurusan', 5.2, False)
R('ae', 'sales', 'Account Executive', [2, 3], ['Penjualan', 'Negosiasi', 'Komunikasi'], ['Microsoft Excel'], [],
  ['mengelola portofolio klien korporasi', 'menyusun penawaran dan kontrak kerja sama', 'memantau pembayaran dan perpanjangan layanan', 'berkoordinasi dengan tim produk untuk kebutuhan klien'],
  ['manage a portfolio of corporate accounts and renewals'], 'Penjualan Korporasi', 'Manajemen atau Komunikasi', 8, False)
R('pc', 'pm', 'Project Coordinator', [1, 2, 3], ['Manajemen Proyek', 'Komunikasi'], ['Agile', 'Microsoft Excel'], [],
  ['mengoordinasikan jadwal dan tugas antar tim proyek', 'memantau progres dan menyusun laporan mingguan', 'melaporkan hambatan kepada pemangku kepentingan', 'menyiapkan notulen rapat dan menindaklanjuti keputusan'],
  ['coordinate schedules and tasks across project teams'], 'Manajemen Proyek', 'Teknik Industri, Manajemen, atau Sistem Informasi', 8)
R('pm', 'pm', 'Product Manager', [2, 3, 4], ['Manajemen Proyek', 'Agile', 'SQL'], ['Analisis Data', 'Figma'], [],
  ['menyusun roadmap produk dan menentukan prioritas fitur', 'menulis kebutuhan fitur bersama tim engineering dan desain', 'memakai data pengguna untuk mengambil keputusan', 'menyampaikan perkembangan produk kepada manajemen'],
  ['own the product roadmap and prioritize features using user data'], 'Produk', 'Teknik Informatika, Manajemen, atau Teknik Industri', 14)
R('sm', 'pm', 'Scrum Master', [3], ['Agile', 'Manajemen Proyek', 'Komunikasi'], ['Git'], [],
  ['memfasilitasi sprint planning, daily stand-up, dan retrospektif', 'menyingkirkan hambatan yang dialami tim', 'menjaga proses Agile berjalan konsisten', 'membantu tim mengukur kecepatan kerja'],
  ['facilitate sprint ceremonies and remove team blockers'], 'Engineering', 'Teknik Informatika atau Manajemen', 12)

# ---------- helpers ----------
def pick_w(pairs):
    tot = sum(w for _, w in pairs)
    r = RNG.uniform(0, tot)
    for v, w in pairs:
        r -= w
        if r <= 0:
            return v
    return pairs[-1][0]

EN_SKILL = {
    'Penjualan': ['sales'], 'Negosiasi': ['negotiation'], 'Komunikasi': ['communication', 'communication skills'],
    'Akuntansi': ['accounting', 'bookkeeping'], 'Pajak': ['taxation', 'tax compliance'], 'Administrasi': ['office administration'],
    'Rekrutmen': ['recruitment', 'talent acquisition'], 'Manajemen Proyek': ['project management'],
    'Customer Service': ['customer service'], 'Analisis Data': ['data analysis'], 'Visualisasi Data': ['data visualization', 'dashboarding'],
    'Statistik': ['statistics'], 'Content Writing': ['content writing'], 'Copywriting': ['copywriting'],
    'Social Media': ['social media'], 'Jaringan Komputer': ['networking'], 'Keamanan Siber': ['cybersecurity', 'information security'],
    'Riset Pengguna': ['user research'], 'Desain Grafis': ['graphic design'], 'Digital Marketing': ['digital marketing'],
    'Video Editing': ['video editing', 'Premiere Pro'], 'Microsoft Office': ['Microsoft Office'], 'Microsoft Excel': ['Excel', 'Microsoft Excel'],
    'UI/UX Design': ['UI/UX design'], 'Machine Learning': ['machine learning'], 'Adobe Photoshop': ['Photoshop'], 'HTML/CSS': ['HTML and CSS'],
    'Pandas': ['Pandas'], 'ETL': ['ETL'], 'Git': ['Git'], 'AWS': ['AWS'],
}
DEPT_EN = {
    'Data': 'Data', 'Data Platform': 'Data Platform', 'Riset': 'Research', 'Business Intelligence': 'Business Intelligence',
    'Strategi Bisnis': 'Business Strategy', 'Operasional': 'Operations', 'Data Science': 'Data Science', 'Machine Learning': 'Machine Learning',
    'AI Bahasa': 'Language AI', 'Engineering': 'Engineering', 'Proyek Web': 'Web Projects', 'Mobile': 'Mobile', 'Infrastruktur': 'Infrastructure',
    'IT Infrastruktur': 'IT Infrastructure', 'IT': 'IT', 'Keamanan Informasi': 'Information Security', 'Desain Produk': 'Product Design',
    'Kreatif': 'Creative', 'Pemasaran': 'Marketing', 'Konten Sosial': 'Social Content', 'Pertumbuhan': 'Growth', 'Konten': 'Content',
    'Produksi Konten': 'Content Production', 'Keuangan': 'Finance', 'Perpajakan': 'Tax', 'Umum': 'General Affairs', 'SDM': 'People',
    'Layanan Pelanggan': 'Customer Support', 'Penjualan': 'Sales', 'Penjualan Korporasi': 'Corporate Sales',
    'Manajemen Proyek': 'Project Management', 'Produk': 'Product',
}

def mention(skill, en=False):
    if en and skill in EN_SKILL:
        return RNG.choice(EN_SKILL[skill])
    return RNG.choice(SK[skill][1])

def article(word):
    return 'an' if word[:1].lower() in 'aeiou' else 'a'

def join_id(items):
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' dan ' + items[-1]

def join_en(items):
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]

def pick_company(role):
    if role['tech']:
        pool = [c for c in COMPANIES if (c[1] & TECH) or ('konsultan' in c[1]) or ('umum' in c[1])]
    else:  # peran non-teknis tidak muncul di perusahaan yang murni teknologi
        pool = [c for c in COMPANIES if c[1] != {'tech'}]
    return RNG.choice(pool)[0]

EXP = {
    0: ['Mahasiswa tingkat akhir atau fresh graduate, tanpa syarat pengalaman.', 'Terbuka untuk mahasiswa semester 6 ke atas.'],
    1: ['Fresh graduate dipersilakan melamar.', 'Pengalaman kerja tidak wajib; pengalaman magang atau proyek kuliah menjadi nilai tambah.'],
    2: ['Pengalaman 1 sampai 2 tahun di bidang serupa.', 'Memiliki pengalaman minimal 1 tahun.'],
    3: ['Pengalaman minimal 3 tahun di bidang serupa.', 'Berpengalaman 3 sampai 5 tahun dan mampu bekerja mandiri.'],
    4: ['Pengalaman minimal 5 tahun dan pernah membimbing anggota tim.', 'Berpengalaman lebih dari 5 tahun, terbiasa mengambil keputusan teknis.'],
}
EXP_EN = {
    0: 'Final-year students and fresh graduates are welcome; no experience required.',
    1: 'Fresh graduates are welcome to apply.',
    2: '1 to 2 years of relevant experience.',
    3: 'At least 3 years of relevant experience.',
    4: '5+ years of experience and a record of mentoring others.',
}
BENEFIT = ['Tersedia BPJS dan tunjangan makan.', 'Jam kerja fleksibel dengan sebagian hari bekerja dari rumah.', 'Ada program pelatihan dan sertifikasi.',
           'Lingkungan kerja yang suportif dan terbuka untuk belajar.', 'Mendapat bimbingan langsung dari tim senior.']
BENEFIT_EN = ['Health insurance and meal allowance provided.', 'Flexible hours with some remote days.', 'Learning budget for courses and certifications.']

def title_for(role, lvl):
    b = role['base']
    if lvl == 0:
        return RNG.choice([f'{b} Intern', f'Magang {b}', f'{b} Internship'])
    if lvl == 1:
        if re.match(r'^(Staf|Admin|Analis)', b):
            return b
        return RNG.choice([f'Junior {b}', f'{b} (Fresh Graduate)', f'{b} Associate'])
    if lvl == 2:
        return RNG.choice([b, b, f'Junior {b}'])
    if lvl == 3:
        return RNG.choice([b, b, f'Mid-level {b}'])
    return f'Senior {b}'

def build_job(i, role=None, level=None):
    role = role or RNG.choice(ROLES)
    lvl = level if level is not None else RNG.choice(role['levels'])
    company = pick_company(role)
    loc = pick_w(LOCS)
    title = title_for(role, lvl)
    etype = 'Magang' if lvl == 0 else pick_w([('Full-time', 82), ('Kontrak', 12), ('Part-time', 6)])
    if lvl == 0 and RNG.random() < .1:
        etype = 'Part-time'
    # skill
    req = list(role['req'])
    if lvl == 0 and len(req) > 2:
        req = req[:2]
    if lvl >= 3 and role['extra'] and RNG.random() < .5:
        req.append(RNG.choice(role['extra']))
    opt = []
    if RNG.random() > .15 and role['opt']:
        k = RNG.randint(1, min(3, len(role['opt'])))
        opt = RNG.sample(role['opt'], k)
        opt = [o for o in opt if o not in req]
    # deskripsi
    english = RNG.random() < .28
    dept = role['dept']
    parts = []
    if english:
        d_en = DEPT_EN.get(dept, dept)
        a = article(title)
        parts.append(RNG.choice([f'{company} is hiring {a} {title} to join the {d_en} team in {loc}.',
                                 f'We are looking for {a} {title} to join our {d_en} team.']))
        r = RNG.sample(role['resp_en'], min(len(role['resp_en']), 2))
        parts.append('You will ' + ' and '.join(r) + '.')
        sk = join_en([mention(s, True) for s in req])
        parts.append(f'Requirements: proficiency in {sk}. {EXP_EN[lvl]}')
        if opt:
            parts.append('Experience with ' + join_en([mention(s, True) for s in opt]) + ' is a plus.')
        if RNG.random() < .4:
            parts.append(RNG.choice(BENEFIT_EN))
    else:
        parts.append(RNG.choice([f'{company} membuka kesempatan untuk posisi {title} di {loc}.',
                                 f'Kami mencari {title} yang akan bergabung dengan tim {dept}.',
                                 f'Tim {dept} di {company} membutuhkan {title}.']))
        n = min(len(role['resp']), RNG.randint(2, 3))
        r = RNG.sample(role['resp'], n)
        parts.append('Tugas utama: ' + join_id(r) + '.')
        edu = role['major']
        edu_txt = 'Pendidikan minimal D3/S1 semua jurusan.' if edu == 'semua jurusan' else f'Pendidikan minimal S1 {edu}.'
        if lvl == 0:
            edu_txt = f'Mahasiswa jurusan {edu}.' if edu != 'semua jurusan' else 'Mahasiswa dari semua jurusan.'
        parts.append(edu_txt)
        sk = join_id([mention(s) for s in req])
        parts.append(RNG.choice([f'Menguasai {sk}.', f'Mampu menggunakan {sk} dengan baik.', f'Memahami dan terbiasa dengan {sk}.']))
        parts.append(RNG.choice(EXP[lvl]))
        if opt:
            parts.append(RNG.choice(['Diutamakan memahami ', 'Nilai tambah jika menguasai ']) + join_id([mention(s) for s in opt]) + '.')
        if RNG.random() < .45:
            parts.append(RNG.choice(BENEFIT))
    if RNG.random() < .06:  # teks berantakan/pendek seperti di portal sungguhan
        parts = [parts[0], parts[1]]
    desc = ' '.join(parts)
    # gaji
    base = role['sal'] * LEVEL_MULT[lvl] * LOC_MULT[loc] * RNG.uniform(.88, 1.15)
    if etype == 'Magang':
        base = RNG.choice([2, 2.5, 3, 3.5, 4]) if True else base
        smin, smax = base, base + RNG.choice([0, .5, 1])
    else:
        smin = round(base * .85 * 2) / 2
        smax = round(base * 1.15 * 2) / 2
        if smax <= smin:
            smax = smin + .5
    hide = RNG.random() < .22
    posted = dt.date(2026, 11, 6) - dt.timedelta(days=int(RNG.triangular(0, 60, 8)))
    deadline = posted + dt.timedelta(days=RNG.choice([14, 21, 30, 30, 45]))
    return dict(job_id=f'J{i:04d}', job_title=title, company=company, description=desc,
                required_skills=';'.join(req), preferred_skills=';'.join(opt),
                experience_level=LEVEL_LABEL[lvl], location=loc, employment_type=etype,
                salary_min='' if hide else f'{smin:g}', salary_max='' if hide else f'{smax:g}',
                posted_at=posted.isoformat(), deadline=deadline.isoformat(), source='sintetis-v1',
                family=role['fam'], dup_of='', _lvl=lvl)

def reword(desc):
    subs = [('Tugas utama:', 'Tanggung jawab:'), ('Menguasai', 'Menguasai dengan baik'), ('Diutamakan', 'Lebih disukai'),
            ('Pengalaman', 'Pengalaman kerja'), ('We are looking for', 'We are hiring'), ('Requirements:', 'Requirements include')]
    for a, b in subs:
        if a in desc and RNG.random() < .7:
            desc = desc.replace(a, b, 1)
    return desc

def main():
    jobs = [build_job(i + 1) for i in range(N_JOBS)]
    # beberapa lowongan hampir kembar (untuk menguji deteksi duplikat)
    for j in RNG.sample(jobs[:N_JOBS], 8):
        i = len(jobs) + 1
        d = dict(j)
        d['job_id'] = f'J{i:04d}'
        d['description'] = reword(j['description'])
        d['posted_at'] = (dt.date.fromisoformat(j['posted_at']) + dt.timedelta(days=RNG.randint(1, 6))).isoformat()
        d['source'] = 'sintetis-v1-repost'
        d['dup_of'] = j['job_id']
        jobs.append(d)
    cols = ['job_id', 'job_title', 'company', 'description', 'required_skills', 'preferred_skills', 'experience_level',
            'location', 'employment_type', 'salary_min', 'salary_max', 'posted_at', 'deadline', 'source', 'family', 'dup_of']
    with open(os.path.join(OUT, 'jobs.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(jobs)

    # kamus skill
    with open(os.path.join(OUT, 'skills.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['skill_id', 'skill_name', 'category', 'aliases'])
        for n, (name, (cat, variants, extra)) in enumerate(SK.items(), 1):
            al = []
            for a in [v.lower() for v in variants] + extra:
                if a != name.lower() and a not in al:
                    al.append(a)
            w.writerow([f'S{n:03d}', name, cat, ';'.join(al)])

    # kueri uji + qrels
    Q = [
     ('Saya menguasai Python, SQL, Pandas, dan visualisasi data. Saya sedang mencari pekerjaan untuk fresh graduate di bidang analisis data.', ['data', 'bi'], ['ml'], 1, None),
     ('mengolah data dan membuat laporan bisnis', ['bi', 'data'], [], None, None),
     ('Saya ingin bekerja membuat dashboard untuk manajemen', ['bi'], ['data'], None, None),
     ('bisa Python dan machine learning, ingin membuat model prediksi', ['ml'], ['data'], None, None),
     ('NLP bahasa Indonesia untuk analisis sentimen media sosial', ['ml'], ['data'], None, None),
     ('membangun aplikasi web dengan JavaScript dan React', ['frontend'], ['design'], None, None),
     ('Saya suka mendesain tampilan aplikasi dan bisa memakai Figma. Mau magang.', ['design'], ['frontend'], 0, None),
     ('backend developer Python Django PostgreSQL', ['backend'], ['devops'], None, None),
     ('membuat REST API dan mengelola database', ['backend'], ['data'], None, None),
     ('mengelola server dan deployment aplikasi di cloud', ['devops'], ['backend'], None, None),
     ('bisa jaringan komputer dan troubleshooting kantor', ['devops'], ['security'], None, None),
     ('keamanan jaringan dan analisis insiden', ['security'], ['devops'], None, None),
     ('mengelola kampanye iklan online dan media sosial', ['marketing'], ['content'], None, None),
     ('menulis artikel SEO dan konten blog', ['content', 'marketing'], [], None, None),
     ('edit video untuk konten TikTok dan Instagram', ['content'], ['marketing', 'design'], None, None),
     ('menyusun laporan keuangan dan menghitung pajak', ['finance'], [], None, None),
     ('lulusan akuntansi cari kerja sebagai fresh graduate', ['finance'], ['admin'], 1, None),
     ('mengurus arsip, surat menyurat, dan jadwal pimpinan', ['admin'], [], None, None),
     ('merekrut karyawan dan mengatur wawancara', ['hr'], [], None, None),
     ('melayani pelanggan lewat chat dan telepon', ['sales'], [], None, None),
     ('mengejar target penjualan dan negosiasi dengan klien', ['sales'], [], None, None),
     ('mengoordinasikan proyek dan memantau progres tim', ['pm'], [], None, None),
     ('menyusun roadmap produk dan menentukan prioritas fitur', ['pm'], ['bi'], None, None),
     ('membuat aplikasi mobile dengan Flutter atau Android', ['mobile'], [], None, None),
     ('magang data analyst di Jakarta', ['data', 'bi'], [], 0, 'Jakarta'),
     ('pekerjaan remote untuk developer Python', ['backend', 'ml'], ['data'], None, 'Remote'),
     ('I enjoy working with data and building reports, no formal experience yet', ['data', 'bi'], [], 1, None),
     ('looking for a UX research and prototyping role', ['design'], [], None, None),
     ('saya punya skill Excel dan akuntansi, cari kerja di Surabaya', ['finance', 'admin'], [], None, 'Surabaya'),
     ('engineer senior berpengalaman membangun data pipeline', ['data'], ['backend'], 4, None),
    ]
    with open(os.path.join(OUT, 'queries.csv'), 'w', newline='', encoding='utf-8') as fq, \
         open(os.path.join(OUT, 'qrels.csv'), 'w', newline='', encoding='utf-8') as fr:
        wq, wr = csv.writer(fq), csv.writer(fr)
        wq.writerow(['query_id', 'query', 'primary_family', 'secondary_family', 'target_level', 'target_location'])
        wr.writerow(['query_id', 'job_id', 'relevance'])
        for n, (text, prim, sec, lv, lc) in enumerate(Q, 1):
            qid = f'Q{n:02d}'
            wq.writerow([qid, text, ';'.join(prim), ';'.join(sec), '' if lv is None else LEVEL_LABEL[lv], lc or ''])
            for j in jobs:
                lvl_ok = lv is None or abs(j['_lvl'] - lv) <= 1
                if j['family'] in prim:
                    g = 2 if lvl_ok else 1
                elif j['family'] in sec and lvl_ok:
                    g = 1
                else:
                    continue
                if lc and j['location'] not in (lc, 'Remote'):
                    g -= 1
                if g > 0:
                    wr.writerow([qid, j['job_id'], g])
    print('selesai:', len(jobs), 'lowongan,', len(SK), 'skill,', len(Q), 'kueri')

if __name__ == '__main__':
    main()
