# auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import uuid
from app.database import get_db
from app.schemas import UserRegister, UserLogin, UserResponse, Token
from app.services.auth_service import register_user, authenticate_user
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models import RefreshToken, User
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/hour")
async def register(request: Request, data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Registrasi user baru, cek email sudah terdaftar atau belum
    user = await register_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return user

@router.post("/login", response_model=Token)
@limiter.limit("5/15minutes")
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    # Autentikasi user berdasarkan email dan password
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Buat access token dan refresh token
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id), "jti": str(uuid.uuid4())})

    # Simpan refresh token ke database
    db_refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    # Cari refresh token yang masih berlaku di database
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Jika token sudah dicabut, cabut semua token user (deteksi reuse)
    if stored_token.revoked_at is not None:
        await db.execute(
            RefreshToken.__table__.update().where(
                RefreshToken.user_id == stored_token.user_id,
                RefreshToken.revoked_at == None
            ).values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Token reuse detected. All sessions revoked.")

    # Pastikan user masih aktif
    user_result = await db.execute(select(User).where(User.id == stored_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found or banned")

    # Cabut token lama dan buat token baru (rotasi)
    stored_token.revoked_at = datetime.now(timezone.utc)

    new_refresh_token_str = create_refresh_token({"sub": str(user.id), "jti": str(uuid.uuid4())})
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_refresh_token)

    access_token = create_access_token({"sub": str(user.id)})

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token_str,
        "token_type": "bearer"
    }

@router.post("/logout", status_code=204)
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cabut refresh token saat logout
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at == None
        )
    )
    stored_token = result.scalar_one_or_none()
    if stored_token:
        stored_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return None