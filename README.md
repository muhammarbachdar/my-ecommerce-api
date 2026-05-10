# 🛒 E-Commerce API

> **Production-ready** e-commerce backend built with **FastAPI**, **PostgreSQL**, and **Docker**. Complete with authentication, product management, shopping cart, orders, and an admin dashboard.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-28.0-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

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
- [License](#-license)

---

## 🚀 Features

### 👤 Customer
| Feature | Description |
|---------|-------------|
| **Authentication** | Register, login, JWT tokens, refresh token, logout. |
| **Products** | Browse, search, filter by category & price, pagination. |
| **Cart** | Add, update quantity, remove items. |
| **Orders** | Checkout from cart, order history, status tracking. |
| **Payments** | Mock payment (ready for real gateway integration). |
| **Reviews** | Rate & review purchased products. |
| **Vouchers** | Claim & apply discount codes. |

### 👑 Admin
| Feature | Description |
|---------|-------------|
| **Product Management** | Full CRUD + image upload to Cloudinary. |
| **Order Control** | Update order status (pending → paid → shipped → delivered). |
| **User Oversight** | View all users, ban/unban accounts. |
| **Voucher Engine** | Create, update, delete discount codes. |
| **Dashboard** | View total orders, revenue, and top products. |

---

## 🛠️ Tech Stack

- **Framework:** FastAPI 0.115.12 [cite: PROJECTS]
- **Database:** PostgreSQL 16 & SQLAlchemy 2.0 (Async) [cite: PROJECTS, 11]
- **Auth:** PyJWT + bcrypt (Refresh Token Rotation) [cite: PROJECTS, 11]
- **File Storage:** Cloudinary API [cite: PROJECTS, 22]
- **Containerization:** Docker & Docker Compose [cite: PROJECTS, 14]
- **Testing:** Pytest & HTTPX [cite: PROJECTS, 16]

---

## ⚡ Quick Start

### Installation
```bash
# Clone repository
git clone https://github.com/muhammarbachdar/my-ecommerce-api.git
cd my-ecommerce-api

# Setup virtual environment
cd backend
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations & start
alembic upgrade head
uvicorn app.main:app --reload
```

---

## 📁 Project Structure
```text
ecommerce-api/
├── backend/
│   ├── app/
│   │   ├── core/          # Security & DB Config
│   │   ├── routers/       # API Endpoints (Auth, Products, etc.)
│   │   ├── models.py      # SQLAlchemy Models
│   │   ├── schemas.py     # Pydantic Schemas
│   │   └── main.py        # Entry Point
│   ├── alembic/           # Migrations
│   └── .env.example
├── docker-compose.yml
└── README.md
```

---

## 📄 License
Distributed under the MIT License.

## 👨‍💻 Author
**M. Ammar Ramadan Bachdar**
[GitHub](https://github.com/muhammarbachdar) | [LinkedIn](https://linkedin.com/in/muhammarbchdr)
