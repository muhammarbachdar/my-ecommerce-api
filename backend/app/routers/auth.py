from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.schemas import UserRegister, UserLogin, UserResponse, Token
from app.services.auth_service import register_user, authenticate_user
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models import RefreshToken, User
from app.core.config import settings
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return user

@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Simpan refresh token ke database
    db_refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    await db.commit()
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# ========== REFRESH TOKEN ==========
@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    # Cek refresh token di database
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Dapatkan user
    user_result = await db.execute(
        select(User).where(User.id == stored_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found or banned")
    
    # Buat access token baru
    access_token = create_access_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# ========== LOGOUT ==========
@router.post("/logout", status_code=204)
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Revoke refresh token
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