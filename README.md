markdown
# Backend E-commerce API

Backend RESTful API untuk aplikasi e-commerce yang dibangun dengan **FastAPI** (async), **PostgreSQL**, **SQLAlchemy 2.0**, dan **Xendit** sebagai payment gateway.

## 📋 Fitur Utama

- ✅ Autentikasi JWT (access token + refresh token)
- ✅ Manajemen produk, kategori, keranjang, wishlist
- ✅ Sistem pesanan dengan voucher diskon
- ✅ Pembayaran via Xendit (invoice)
- ✅ Review & rating produk
- ✅ Admin dashboard (statistik, manajemen order, voucher)
- ✅ Soft delete pada entitas penting
- ✅ Rate limiting & logging terstruktur
- ✅ Unit testing (pytest)

## 🛠 Tech Stack

| Komponen          | Teknologi                           |
|-------------------|-------------------------------------|
| Framework         | FastAPI                             |
| Database          | PostgreSQL (via asyncpg)            |
| ORM               | SQLAlchemy 2.0 (asyncio)            |
| Autentikasi       | JWT (python-jose) + bcrypt          |
| Payment Gateway   | Xendit (invoice)                    |
| Rate Limiting     | slowapi (Redis optional)            |
| Migrasi Database  | Alembic                             |
| Upload Gambar     | Cloudinary                          |
| Testing           | pytest, httpx, SQLite in-memory     |
| Logging           | Loguru                              |

## 🚀 Cara Menjalankan

### 1. Prasyarat

- Python 3.10+
- PostgreSQL (running)
- (Opsional) Redis untuk rate limiting production
- Akun [Xendit](https://www.xendit.co/) untuk payment gateway

### 2. Clone Repository

```bash
git clone https://github.com/your-repo/ecommerce-backend.git
cd ecommerce-backend

### 3. Buat Virtual Environment

```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
# atau
venv\Scripts\activate          # Windows

### 4. Install Dependencies

```bash
pip install -r requirements.txt

### 5. Konfigurasi Environment

Buat file `.env` di root proyek:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# JWT
SECRET_KEY=minimal32karakterSuperRahasiaJanganKebocor
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Xendit
XENDIT_SECRET_KEY=xnd_development_xxxxx
XENDIT_WEBHOOK_TOKEN=your_webhook_verification_token
XENDIT_API_BASE_URL=[https://api.xendit.co](https://api.xendit.co)

# Cloudinary (opsional)
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx

# Redis (opsional, untuk rate limiting production)
REDIS_URL=redis://localhost:6379

# Database echo (true untuk debug SQL)
DB_ECHO=False

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

### 6. Jalankan Migrasi Database

```bash
alembic upgrade head

### 7. Jalankan Server (Development)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### 8. Dokumentasi API Interaktif

- [cite_start]**Swagger UI:** `http://localhost:8000/docs` [cite: 21]
- [cite_start]**ReDoc:** `http://localhost:8000/redoc` [cite: 21]

## [cite_start]📁 Struktur Proyek [cite: 21]

```text
backend/
├── app/
[cite_start]│   ├── core/               # Konfigurasi, security, logging, rate limiter [cite: 21]
[cite_start]│   ├── middleware/         # Request ID middleware [cite: 21]
[cite_start]│   ├── models.py           # SQLAlchemy models [cite: 21]
[cite_start]│   ├── schemas.py          # Pydantic schemas [cite: 21]
[cite_start]│   ├── database.py         # Engine & session [cite: 21]
[cite_start]│   ├── routers/            # Endpoints per resource [cite: 21, 22]
[cite_start]│   │   ├── auth.py [cite: 22]
[cite_start]│   │   ├── users.py [cite: 22]
[cite_start]│   │   ├── products.py [cite: 22]
[cite_start]│   │   ├── categories.py [cite: 22]
[cite_start]│   │   ├── carts.py [cite: 22]
[cite_start]│   │   ├── orders.py [cite: 22]
[cite_start]│   │   ├── payments.py [cite: 22]
[cite_start]│   │   ├── wishlist.py [cite: 22]
[cite_start]│   │   ├── reviews.py [cite: 22]
[cite_start]│   │   ├── vouchers.py [cite: 22]
[cite_start]│   │   ├── addresses.py [cite: 22]
[cite_start]│   │   └── admin.py [cite: 23]
[cite_start]│   ├── services/           # Business logic (Xendit, auth, review) [cite: 23]
[cite_start]│   └── utils/              # Pagination, uploader [cite: 23]
[cite_start]├── tests/                  # Pytest test suite [cite: 23]
[cite_start]├── alembic/                # Migrations [cite: 23]
[cite_start]├── .env [cite: 23]
[cite_start]├── requirements.txt [cite: 23]
[cite_start]└── main.py                 # Entry point [cite: 23, 24]

## [cite_start]🔐 Autentikasi 

[cite_start]Semua endpoint (kecuali public) memerlukan header: 

```text
Authorization: Bearer <access_token>

| Endpoint | Method | Deskripsi |
|---|---|---|
| `/api/v1/auth/register` | `POST` | Daftar user baru |
| `/api/v1/auth/login` | `POST` | Login → dapat access & refresh token |
| `/api/v1/auth/refresh` | `POST` | Perpanjang access token |
| `/api/v1/auth/logout` | `POST` | Logout (revoke refresh token) |

[cite_start]*Role Admin: Endpoint khusus admin hanya bisa diakses jika `User.is_admin = True`.* [cite: 24]

## 📡 Endpoint API Utama

[cite_start]**Prefix semua endpoint:** `/api/v1` [cite: 25]

### [cite_start]Produk [cite: 25]
| Method | Endpoint | Auth |
|---|---|---|
| `GET` | `/products/` | - |
| `GET` | `/products/{id}` | - |
| `POST` | `/products/` | Admin |
| `PUT` | `/products/{id}` | Admin |
| `DELETE` | `/products/{id}` | Admin |

### [cite_start]Keranjang [cite: 25]
| Method | Endpoint | Auth |
|---|---|---|
| `GET` | `/carts/` | Bearer |
| `POST` | `/carts/` | Bearer |
| `PUT` | `/carts/{item_id}` | Bearer |
| `DELETE` | `/carts/{item_id}` | Bearer |

### [cite_start]Pesanan [cite: 25]
| Method | Endpoint | Auth |
|---|---|---|
| `POST` | `/orders/` | Bearer |
| `GET` | `/orders/me` | Bearer |
| `GET` | `/orders/{id}` | Bearer |
| `PATCH` | `/orders/{id}/user-cancel` | Bearer |
| `PATCH` | `/orders/{id}/status` | Admin |
| `GET` | `/orders/` | Admin |

### [cite_start]Voucher [cite: 25]
| Method | Endpoint | Auth |
|---|---|---|
| `GET` | `/vouchers/available` | Bearer |
| `GET` | `/vouchers/my` | Bearer |
| `POST` | `/vouchers/{id}/claim` | Bearer |
| `POST` | `/vouchers/apply` | Bearer |
| `POST` | `/vouchers/admin` | Admin |
| `PUT` | `/vouchers/admin/{id}` | Admin |
| `DELETE` | `/vouchers/admin/{id}` | Admin |

### [cite_start]Pembayaran (Xendit) [cite: 25]
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/payments/xendit/webhook` | [cite_start]Webhook dari Xendit (public) [cite: 25] |

[cite_start]*Catatan: Endpoint `POST /orders/` akan otomatis membuat invoice Xendit dan mengembalikan `invoice_url`.* [cite: 25]

## 🔄 Alur Pembayaran Xendit

1. User checkout → `POST /orders/` dengan `cart_item_ids`.
2. Backend membuat order (status pending), mengurangi stok, lalu memanggil Xendit API → mendapat `invoice_url`.
3. Response order berisi `invoice_url`.
4. Frontend membuka URL tersebut (via `url_launcher`).
5. User melakukan pembayaran di halaman Xendit.
6. Xendit mengirim webhook `POST /payments/xendit/webhook` (verifikasi token, update status order menjadi paid, tandai voucher terpakai).
7. User bisa cek status pembayaran via `GET /orders/{id}`.

## 🧪 Testing

Jalankan semua test (menggunakan database SQLite in-memory):

```bash
pytest tests/ -v

## [cite_start]📦 Deployment ke Production 

[cite_start]Gunakan Gunicorn + Uvicorn workers: 

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

- [cite_start]Set `DB_ECHO=False` di `.env`[cite: 32].
- [cite_start]Gunakan Redis untuk rate limiting production (ubah `limiter.py`)[cite: 32].
- [cite_start]Pastikan `SECRET_KEY` panjang > 32 karakter dan aman[cite: 32].
- [cite_start]Set `ALLOWED_ORIGINS` sesuai domain frontend[cite: 33].

## 🌐 Environment Variables (Lengkap)

| Variabel | Wajib | Default |
|---|---|---|
| `DATABASE_URL` | ✅ | - |
| `SECRET_KEY` | ✅ | - (min 32 chars) |
| `XENDIT_SECRET_KEY` | ✅ | - |
| `XENDIT_WEBHOOK_TOKEN` | ✅ | - |
| `ALGORITHM` | ❌ | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | 7 |
| `DB_ECHO` | ❌ | False |
| `ALLOWED_ORIGINS` | ❌ | http://localhost:3000,http://localhost:3001 |
| `REDIS_URL` | ❌ | None |
| `CLOUDINARY_CLOUD_NAME` | ❌ | "" |
| `CLOUDINARY_API_KEY` | ❌ | "" |
| `CLOUDINARY_API_SECRET` | ❌ | "" |

## 👨‍💻 Pengembang

Dibuat dengan ❤️ oleh M Amar Ramadan Bachdar menggunakan FastAPI.

## 📄 Lisensi

[cite_start]MIT [cite: 33]

