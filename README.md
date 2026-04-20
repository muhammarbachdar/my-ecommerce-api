# 🛒 E-Commerce API

> Production-ready e-commerce backend built with FastAPI, PostgreSQL, and Docker. Complete with authentication, product management, shopping cart, orders, payments, reviews, vouchers, and admin dashboard.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-28.0-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🚀 Live Demo

Test the API yourself:  
👉 [https://my-ecommerce-api.up.railway.app/docs](https://my-ecommerce-api.up.railway.app/docs)

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [Environment Variables](#-environment-variables)
- [Deployment](#-deployment)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Purchase](#-purchase-full-source-code)
- [License](#-license)

---

## 🚀 Features

### 👤 Customer
| Feature | Description |
|---------|-------------|
| Authentication | Register, login, JWT tokens, refresh token, logout |
| Products | Browse, search, filter by category & price, pagination |
| Cart | Add, update quantity, remove items |
| Wishlist | Save favorite products |
| Orders | Checkout from cart, order history, status tracking |
| Payments | Mock payment (ready for real gateway integration) |
| Reviews | Rate & review purchased products |
| Vouchers | Claim & apply discount codes |
| Addresses | Manage multiple shipping addresses |

### 👑 Admin
| Feature | Description |
|---------|-------------|
| Products | Full CRUD + image upload to Cloudinary |
| Categories | Full CRUD with slug management |
| Orders | Update order status (pending → paid → shipped → delivered) |
| Users | View all users, ban/unban accounts |
| Vouchers | Create, update, delete discount codes |
| Dashboard | View total orders, revenue, top products, revenue by month |

### 🔒 Security
- JWT authentication with refresh token rotation
- Role-based access control (User / Admin)
- Password hashing with bcrypt
- Soft delete (data preserved)
- SQL injection protection via SQLAlchemy ORM

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI 0.115.12 |
| **Language** | Python 3.12 |
| **Database** | PostgreSQL 16 |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migration** | Alembic |
| **Auth** | PyJWT + python-jose + bcrypt |
| **Validation** | Pydantic 2.10 |
| **File Storage** | Cloudinary |
| **Container** | Docker + Docker Compose |
| **Testing** | Pytest + HTTPX |
| **Docs** | Swagger UI (/docs) & ReDoc (/redoc) |

---

## ⚡ Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Cloudinary account (for image upload)

### Installation

```bash
# Clone repository
git clone https://github.com/muhammarbachdar/my-ecommerce-api.git
cd my-ecommerce-api

# Copy environment variables
cp backend/.env.example backend/.env

# Edit .env with your values (see Environment Variables section)
nano backend/.env

# Start PostgreSQL via Docker
docker-compose up -d postgres

# Setup virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Create admin user (optional)
# Register via API first, then set as admin:
# docker exec -it ecommerce-api-postgres-1 psql -U postgres -d ecommerce -c "UPDATE users SET is_admin = TRUE WHERE id = 1;"

# Start the server
uvicorn app.main:app --reload
Run with Docker Compose (All Services)
bash
docker-compose up -d
Access API at: http://localhost:8000

📚 API Documentation
Once the server is running, visit:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

Key Endpoints
Method	Endpoint	Description	Auth
POST	/auth/register	Register new user	Public
POST	/auth/login	Login & get tokens	Public
POST	/auth/refresh	Refresh access token	Public
POST	/auth/logout	Logout & revoke token	User
GET	/products	List products (paginated, search, filter)	Public
GET	/products/{id}	Get product details	Public
POST	/cart	Add to cart	User
GET	/cart	Get cart	User
POST	/orders	Checkout	User
GET	/orders/me	Get my orders	User
POST	/payments	Create payment	User
GET	/wishlist	Get wishlist	User
POST	/reviews	Add review	User
GET	/vouchers/available	Get available vouchers	User
POST	/vouchers/{id}/claim	Claim voucher	User
GET	/admin/dashboard	Dashboard stats	Admin
POST	/products	Create product	Admin
PUT	/products/{id}	Update product	Admin
DELETE	/products/{id}	Delete product	Admin
🔧 Environment Variables
Create a .env file in backend/ directory:

ini
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ecommerce

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Cloudinary (for image upload)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Email (optional)
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
MAIL_SERVER=
MAIL_PORT=587
🌐 Deployment
Deploy to Railway (Recommended)
Push your code to GitHub

Sign up at Railway.app

Click New Project → Deploy from GitHub repo

Select your repository

Add environment variables (from .env.example)

Railway will auto-deploy on every push

Deploy to VPS (DigitalOcean, AWS, etc.)
bash
# Install Docker on VPS
# Copy project to server
scp -r ./my-ecommerce-api user@your-server:/app

# SSH into server and run
cd /app/my-ecommerce-api
docker-compose up -d
📁 Project Structure
text
ecommerce-api/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Settings management
│   │   │   ├── database.py        # DB connection
│   │   │   └── security.py        # JWT, password hashing
│   │   ├── routers/
│   │   │   ├── auth.py            # Authentication endpoints
│   │   │   ├── products.py        # Product CRUD
│   │   │   ├── categories.py      # Category CRUD
│   │   │   ├── carts.py           # Shopping cart
│   │   │   ├── orders.py          # Order management
│   │   │   ├── payments.py        # Mock payment
│   │   │   ├── wishlist.py        # Wishlist
│   │   │   ├── reviews.py         # Product reviews
│   │   │   ├── vouchers.py        # Discount codes
│   │   │   ├── addresses.py       # Shipping addresses
│   │   │   ├── users.py           # User management
│   │   │   └── admin.py           # Admin dashboard
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # Pydantic schemas
│   │   ├── utils/
│   │   │   ├── pagination.py      # Pagination helper
│   │   │   └── uploader.py        # Cloudinary upload
│   │   └── main.py                # FastAPI entry point
│   ├── alembic/                   # Database migrations
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
🧪 Testing
bash
cd backend
pytest
Test coverage includes:

Authentication flow

Product CRUD

Cart operations

Order checkout

Admin role protection

Voucher validation

📦 Purchase Full Source Code
Get the complete source code with:

✅ All features listed above

✅ Docker setup ready for production

✅ Cloudinary integration

✅ Alembic migrations

✅ Postman collection

✅ Lifetime updates

👉 Buy on Gumroad

📄 License
Distributed under the MIT License. See LICENSE for more information.

👨‍💻 Author
M. Ammar Ramadan Bachdar

GitHub: @muhammarbachdar

LinkedIn: muhammarbchdr

⭐ Support
If this project helps you, please give it a ⭐ on GitHub!

📞 Contact
For support or custom development inquiries:
📧 muhammarbachdar@gmail.com

Built with ❤️ using FastAPI

text

---

## ✅ **Simpan README.md di Repo Private**

```bash
cd d:/ecomerce-api
git add README.md
git commit -m "docs: update README with live demo and purchase section"
git push origin main