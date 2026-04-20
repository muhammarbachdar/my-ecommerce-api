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

router = APIRouter(prefix="/vouchers", tags=["vouchers"])

# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin", response_model=VoucherResponse, status_code=201)
async def create_voucher(
    voucher_data: VoucherCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    result = await db.execute(
        select(Voucher).where(Voucher.code == voucher_data.code.upper())
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Voucher code already exists")
    
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
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Voucher).where(
            Voucher.id == voucher_id,
            Voucher.is_active == True,
            Voucher.start_date <= now,
            Voucher.end_date >= now,
            Voucher.used_count < Voucher.usage_limit
        )
    )
    voucher = result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not available")
    
    existing = await db.execute(
        select(UserVoucher).where(
            UserVoucher.user_id == current_user.id,
            UserVoucher.voucher_id == voucher_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already claimed this voucher")
    
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
    
    db_user_voucher = UserVoucher(
        user_id=current_user.id,
        voucher_id=voucher_id
    )
    db.add(db_user_voucher)
    await db.commit()
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

# Apply voucher to order
@router.post("/apply")
async def apply_voucher(
    apply_data: ApplyVoucher,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek order
    order_result = await db.execute(
        select(Order).where(
            Order.id == apply_data.order_id,
            Order.user_id == current_user.id,
            Order.status == "pending"
        )
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or already paid")
    
    # Cek voucher
    now = datetime.now(timezone.utc)
    voucher_result = await db.execute(
        select(Voucher).where(
            Voucher.code == apply_data.code.upper(),
            Voucher.is_active == True,
            Voucher.start_date <= now,
            Voucher.end_date >= now,
            Voucher.used_count < Voucher.usage_limit
        )
    )
    voucher = voucher_result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=400, detail="Invalid or expired voucher code")
    
    # Cek min purchase
    if order.total_price < voucher.min_purchase:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum purchase Rp{int(voucher.min_purchase):,} required"
        )
    
    # Cek usage per user
    user_usage = await db.execute(
        select(func.count()).select_from(VoucherUsage).where(
            VoucherUsage.user_id == current_user.id,
            VoucherUsage.voucher_id == voucher.id
        )
    )
    used_by_user = user_usage.scalar() or 0
    if used_by_user >= voucher.usage_per_user:
        raise HTTPException(status_code=400, detail="Voucher usage limit reached for this user")
    
    # Cek apakah voucher sudah pernah dipake untuk order ini
    existing_usage = await db.execute(
        select(VoucherUsage).where(VoucherUsage.order_id == apply_data.order_id)
    )
    if existing_usage.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Voucher already applied to this order")
    
    # Calculate discount
    if voucher.discount_type == "percentage":
        discount = order.total_price * voucher.discount_value / 100
        if voucher.max_discount and discount > voucher.max_discount:
            discount = voucher.max_discount
    else:
        discount = min(voucher.discount_value, order.total_price)
    
    original_total = order.total_price
    final_price = original_total - discount
    
    # Update order total_price
    order.total_price = final_price
    await db.commit()
    
    return {
        "original_total": original_total,
        "discount": discount,
        "final_total": final_price,
        "voucher_code": voucher.code,
        "voucher_name": voucher.name
    }

# Confirm voucher usage (after payment)
@router.post("/confirm")
async def confirm_voucher(
    apply_data: ApplyVoucher,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek order
    order_result = await db.execute(
        select(Order).where(
            Order.id == apply_data.order_id,
            Order.user_id == current_user.id,
            Order.status == "paid"
        )
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not paid")
    
    # Cek voucher
    voucher_result = await db.execute(
        select(Voucher).where(Voucher.code == apply_data.code.upper())
    )
    voucher = voucher_result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status_code=400, detail="Voucher not found")
    
    # Hitung diskon
    if voucher.discount_type == "percentage":
        discount = order.total_price * voucher.discount_value / 100
        if voucher.max_discount and discount > voucher.max_discount:
            discount = voucher.max_discount
    else:
        discount = min(voucher.discount_value, order.total_price)
    
    # Update voucher used_count
    voucher.used_count += 1
    
    # Create voucher usage record
    db_usage = VoucherUsage(
        voucher_id=voucher.id,
        user_id=current_user.id,
        order_id=order.id,
        discount_amount=discount
    )
    db.add(db_usage)
    
    # Update user_voucher if exists
    user_voucher_result = await db.execute(
        select(UserVoucher).where(
            UserVoucher.user_id == current_user.id,
            UserVoucher.voucher_id == voucher.id,
            UserVoucher.is_used == False
        )
    )
    user_voucher = user_voucher_result.scalar_one_or_none()
    if user_voucher:
        user_voucher.is_used = True
        user_voucher.used_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"message": "Voucher applied successfully"}