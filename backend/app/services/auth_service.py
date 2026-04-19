from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
from app.core.security import hash_password, verify_password

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def register_user(db: AsyncSession, email: str, password: str):
    existing = await get_user_by_email(db, email)
    if existing:
        return None
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user