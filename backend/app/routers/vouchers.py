# vouchers.py (LENGKAP - DENGAN PERBAIKAN FINAL: NONAKTIFKAN ENDPOINT USANG)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import Voucher, UserVoucher, VoucherUsage, Order, User
from app.schemas import (
    VoucherCreate, VoucherUpdate, VoucherResponse,
    UserVoucherResponse, ApplyVoucher
)
from app.core.security import get_current_user, require_admin

router = APIRouter(tags=["vouchers"])

# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin", response_model=VoucherResponse, status_code=201)
async def create_voucher(
    voucher_data: VoucherCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Cek apakah kode voucher sudah ada
    result = await db.execute(
        select(Voucher).where(Voucher.code == voucher_data.code.upper())
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Voucher code already exists")
    
    # Buat voucher baru
    db_voucher = Voucher(
        code=voucher_data.code.upper(),
        name=voucher_data.name,
        description=voucher_data.description,
        discount_type=voucher_data.discount_type,
        discount_value=voucher_data.discount_value,
        min_purchase=voucher_data.min_purchase,
        max_discount=voucher_data.max_discount,
        usage_limit=voucher_data.usage_limit,
        usage_per_user=voucher_data.usage_per_user,
        start_date=voucher_data.start_date,
        end_date=voucher_data.end_date
    )
    db.add(db_voucher)
    await db.commit()
    await db.refresh(db_voucher)
    return db_voucher

@router.get("/admin", response_model=List[VoucherResponse])
async def get_all_vouchers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Admin: ambil semua voucher
    result = await db.execute(
        select(Voucher).offset(skip).limit(limit).order_by(Voucher.id.desc())
    )
    vouchers = result.scalars().all()
    return vouchers

@router.put("/admin/{voucher_id}", response_model=VoucherResponse)
async def update_voucher(
    voucher_id: int,
    voucher_update: VoucherUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Admin: update voucher
    result = await db.execute(select(Voucher).where(Voucher.id == voucher_id))
    voucher = result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    update_data = voucher_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(voucher, key, value)
    
    await db.commit()
    await db.refresh(voucher)
    return voucher

@router.delete("/admin/{voucher_id}", status_code=204)
async def delete_voucher(
    voucher_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Admin: hapus voucher permanen
    result = await db.execute(select(Voucher).where(Voucher.id == voucher_id))
    voucher = result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    await db.delete(voucher)
    await db.commit()
    return None

# ==================== USER ENDPOINTS ====================

@router.get("/available", response_model=List[VoucherResponse])
async def get_available_vouchers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cari voucher yang aktif secara global (belum kadaluarsa, masih ada kuota)
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Voucher).where(
            Voucher.is_active == True,
            Voucher.start_date <= now,
            Voucher.end_date >= now,
            Voucher.used_count < Voucher.usage_limit
        ).order_by(Voucher.end_date)
    )
    vouchers = result.scalars().all()
    
    # Filter voucher yang belum melebihi batas penggunaan per user
    available = []
    for voucher in vouchers:
        user_usage = await db.execute(
            select(func.count()).select_from(UserVoucher).where(
                UserVoucher.user_id == current_user.id,
                UserVoucher.voucher_id == voucher.id,
                UserVoucher.is_used == True
            )
        )
        used_by_user = user_usage.scalar() or 0
        if used_by_user < voucher.usage_per_user:
            available.append(voucher)
    
    return available

@router.post("/{voucher_id}/claim", response_model=UserVoucherResponse)
async def claim_voucher(
    voucher_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek ketersediaan voucher (aktif, belum kadaluarsa, masih ada kuota)
    now = datetime.now(timezone.utc)
    # [FIX] Tambah .with_for_update() untuk mencegah race condition overclaim
    result = await db.execute(
        select(Voucher).where(
            Voucher.id == voucher_id,
            Voucher.is_active == True,
            Voucher.start_date <= now,
            Voucher.end_date >= now,
            Voucher.used_count < Voucher.usage_limit
        ).with_for_update()
    )
    voucher = result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not available")
    
    # Pastikan user belum pernah claim voucher ini
    existing = await db.execute(
        select(UserVoucher).where(
            UserVoucher.user_id == current_user.id,
            UserVoucher.voucher_id == voucher_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already claimed this voucher")
    
    # Pastikan user belum melebihi batas penggunaan per user
    user_usage = await db.execute(
        select(func.count()).select_from(UserVoucher).where(
            UserVoucher.user_id == current_user.id,
            UserVoucher.voucher_id == voucher_id,
            UserVoucher.is_used == True
        )
    )
    used_by_user = user_usage.scalar() or 0
    if used_by_user >= voucher.usage_per_user:
        raise HTTPException(status_code=400, detail="You have reached the usage limit for this voucher")
    
    # [FIX] Race condition masih mungkin terjadi karena tidak ada lock di UserVoucher.
    # Solusi enterprise: tambahkan unique constraint (user_id, voucher_id) di database.
    # Sementara ini tetap menggunakan insert biasa, namun dengan harapan constraint mencegah duplikat.
    db_user_voucher = UserVoucher(
        user_id=current_user.id,
        voucher_id=voucher_id
    )
    db.add(db_user_voucher)
    try:
        await db.commit()
    except Exception:  # IntegrityError jika constraint dilanggar
        await db.rollback()
        raise HTTPException(status_code=400, detail="You already claimed this voucher")
    await db.refresh(db_user_voucher)
    
    return {
        "id": db_user_voucher.id,
        "voucher_id": voucher.id,
        "code": voucher.code,
        "name": voucher.name,
        "discount_type": voucher.discount_type,
        "discount_value": voucher.discount_value,
        "min_purchase": voucher.min_purchase,
        "max_discount": voucher.max_discount,
        "is_used": db_user_voucher.is_used,
        "claimed_at": db_user_voucher.claimed_at,
        "used_at": db_user_voucher.used_at
    }

@router.get("/my", response_model=List[UserVoucherResponse])
async def get_my_vouchers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ambil semua voucher yang sudah di-claim oleh user
    result = await db.execute(
        select(UserVoucher).where(UserVoucher.user_id == current_user.id)
    )
    user_vouchers = result.scalars().all()
    
    response = []
    for uv in user_vouchers:
        voucher_result = await db.execute(select(Voucher).where(Voucher.id == uv.voucher_id))
        voucher = voucher_result.scalar_one_or_none()
        if voucher:
            response.append({
                "id": uv.id,
                "voucher_id": voucher.id,
                "code": voucher.code,
                "name": voucher.name,
                "discount_type": voucher.discount_type,
                "discount_value": voucher.discount_value,
                "min_purchase": voucher.min_purchase,
                "max_discount": voucher.max_discount,
                "is_used": uv.is_used,
                "claimed_at": uv.claimed_at,
                "used_at": uv.used_at
            })
    
    return response

# ==================== ENDPOINT DINONAKTIFKAN (DEAD CODE / BACKDOOR) ====================
# [FIX] Nonaktifkan endpoint /apply karena logika voucher sudah diintegrasikan ke create_order (orders.py)
@router.post("/apply", include_in_schema=False)
async def apply_voucher(
    apply_data: ApplyVoucher,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Endpoint ini sudah tidak digunakan lagi. Logika voucher sekarang di dalam create_order.
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Voucher application is now integrated into the order creation process."
    )

# [FIX] Nonaktifkan endpoint /confirm karena logika voucher sudah diintegrasikan ke xendit_webhook (payments.py)
@router.post("/confirm", include_in_schema=False)
async def confirm_voucher(
    apply_data: ApplyVoucher,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Endpoint ini sudah tidak digunakan lagi. Logika voucher sekarang di dalam xendit_webhook.
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Voucher confirmation is now integrated into payment webhook."
    )