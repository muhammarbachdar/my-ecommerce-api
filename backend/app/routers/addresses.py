# addresses.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models import Address, User
from app.schemas import AddressCreate, AddressUpdate, AddressResponse
from app.core.security import get_current_user, require_admin
from app.utils.pagination import paginated_response

router = APIRouter(tags=["addresses"])

@router.get("/", response_model=dict)
async def get_my_addresses(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_result = await db.execute(
        select(func.count()).select_from(Address).where(
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Address)
        .where(
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    addresses = result.scalars().all()
    return paginated_response(addresses, page, limit, total)

@router.post("/", response_model=AddressResponse, status_code=201)
async def create_address(
    address_data: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if address_data.is_default:
        result = await db.execute(
            select(Address).where(
                Address.user_id == current_user.id,
                Address.is_deleted == False
            )
        )
        existing_addresses = result.scalars().all()
        for addr in existing_addresses:
            addr.is_default = False

    db_address = Address(
        user_id=current_user.id,
        label=address_data.label,
        recipient_name=address_data.recipient_name,
        phone=address_data.phone,
        full_address=address_data.full_address,
        city=address_data.city,
        province=address_data.province,
        postal_code=address_data.postal_code,
        is_default=address_data.is_default
    )
    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)
    return db_address

@router.get("/admin/user/{user_id}", response_model=dict)
async def get_addresses_by_user(
    user_id: int,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total_result = await db.execute(
        select(func.count()).select_from(Address).where(
            Address.user_id == user_id,
            Address.is_deleted == False
        )
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Address)
        .where(
            Address.user_id == user_id,
            Address.is_deleted == False
        )
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    addresses = result.scalars().all()
    return paginated_response(addresses, page, limit, total)

@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address

@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int,
    address_update: AddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail=f"Address with id {address_id} not found")

    update_data = address_update.model_dump(exclude_unset=True)

    if update_data.get("is_default") and not address.is_default:
        result = await db.execute(
            select(Address).where(
                Address.user_id == current_user.id,
                Address.is_deleted == False
            )
        )
        existing_addresses = result.scalars().all()
        for addr in existing_addresses:
            addr.is_default = False

    for key, value in update_data.items():
        setattr(address, key, value)

    await db.commit()
    await db.refresh(address)
    return address

@router.delete("/{address_id}", status_code=204)
async def delete_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail=f"Address with id {address_id} not found")

    count_result = await db.execute(
        select(func.count()).select_from(Address).where(
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
    )
    count = count_result.scalar()

    # Simpan nilai is_default sebelum soft delete dan commit
    was_default = address.is_default

    address.is_deleted = True
    address.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # Gunakan was_default, bukan address.is_default (yang sudah stale setelah commit)
    if was_default and count > 1:
        first_address_result = await db.execute(
            select(Address).where(
                Address.user_id == current_user.id,
                Address.is_deleted == False
            ).order_by(Address.created_at.asc()).limit(1)
        )
        first_address = first_address_result.scalar_one_or_none()
        if first_address:
            first_address.is_default = True
            await db.commit()

    return None

# ==================== PATCH 3: set-default endpoint ====================
@router.patch("/{address_id}/set-default", response_model=AddressResponse)
async def set_default_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Lock dan cari alamat target
    result = await db.execute(
        select(Address)
        .where(
            Address.id == address_id,
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
        .with_for_update()
    )
    target_address = result.scalar_one_or_none()
    if not target_address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Idempotent: jika sudah default, langsung return
    if target_address.is_default:
        await db.refresh(target_address)
        return target_address

    # Reset semua alamat user menjadi non-default menggunakan UPDATE langsung
    await db.execute(
        update(Address)
        .where(
            Address.user_id == current_user.id,
            Address.is_deleted == False
        )
        .values(is_default=False)
        .execution_options(synchronize_session="fetch")
    )

    # Set alamat target menjadi default
    target_address.is_default = True
    await db.commit()
    await db.refresh(target_address)
    return target_address