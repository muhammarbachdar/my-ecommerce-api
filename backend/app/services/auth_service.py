# auth_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
from app.core.security import hash_password, verify_password

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def register_user(db: AsyncSession, email: str, password: str):
    # Cek apakah email sudah terdaftar
    existing = await get_user_by_email(db, email)
    if existing:
        return None
    # Hash password dan simpan user baru
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    # Ambil user berdasarkan email
    user = await get_user_by_email(db, email)
    if not user:
        return None
    # Verifikasi password
    if not verify_password(password, user.hashed_password):
        return None
    return user