# Gerdiary API

Backend HTTP Gerdiary untuk identitas dan sesi pengguna, journal makanan dan gejala, kategori, pengeluaran, nutrisi, serta keselamatan. Dibangun dengan Flask, SQLAlchemy, Alembic, dan PostgreSQL.

## Persyaratan

- Python 3.12 atau lebih baru
- PostgreSQL untuk pengembangan dan pengujian

## Instalasi

Dari root repository Gerdiary API:

```bash
python -m venv .venv
```

Aktifkan virtual environment, lalu jalankan:

```bash
python -m pip install -e ".[dev]"
```

Salin `.env.example` ke `.env`, lalu sesuaikan nilai untuk lingkungan lokal. Jangan commit `.env` atau kredensial.

```bash
flask --app wsgi.py db upgrade
flask --app wsgi.py run --debug
```

API berjalan di `http://127.0.0.1:5000`. Frontend Vite meneruskan permintaan `/api` ke alamat ini secara default.

## Konfigurasi

Konfigurasi dibaca dari environment atau `.env`:

| Variabel | Kegunaan |
| --- | --- |
| `APP_ENV` | Lingkungan aplikasi |
| `DATABASE_URL` | Koneksi database pengembangan |
| `TEST_DATABASE_URL` | Koneksi database khusus test |
| `SECRET_KEY` | Kunci keamanan aplikasi |
| `JWT_SECRET_KEY` | Kunci penandatanganan sesi JWT |
| `FRONTEND_ORIGIN` | Origin frontend untuk pemeriksaan request |
| `COOKIE_SECURE` | Aktifkan cookie Secure saat HTTPS |
| `NUTRITION_BASE_URL` | Override URL provider nutrisi, bila diperlukan |
| `NUTRITION_TIMEOUT_SECONDS` | Batas waktu permintaan provider nutrisi |

Gunakan kredensial acak yang kuat untuk `SECRET_KEY` dan `JWT_SECRET_KEY`. Jangan gunakan nilai contoh di production.

## Perintah

Jalankan dari root repository dengan virtual environment aktif:

```bash
ruff check .
mypy src
pytest tests -q
```

Integration test memerlukan `TEST_DATABASE_URL` yang menunjuk ke database test terpisah. Jangan arahkan integration test ke database pengembangan.

## Migrasi database

```bash
flask --app wsgi.py db upgrade
```

Migrasi berada di `migrations/versions/` dan dikelola dengan Alembic melalui Flask-Migrate.

## Struktur

```text
src/gerdiary/
├── modules/          # Fitur dan aturan domain
├── shared/           # Kebijakan lintas fitur
└── infrastructure/   # Database dan adapter provider
migrations/           # Migrasi skema
tests/                 # Unit dan integration test
wsgi.py                # Entry point Flask
```

Gunakan `.env.example` sebagai daftar variabel yang dibutuhkan. Hapus atau samarkan data pribadi sebelum menyimpan fixture dan log.
