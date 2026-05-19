# wishlist.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models import Wishlist, Product, User
from app.schemas import WishlistCreate, WishlistResponse
from app.core.security import get_current_user
from app.utils.pagination import paginated_response   # FIX: import

router = APIRouter(tags=["wishlist"])

@router.get("/", response_model=dict)   # FIX: ubah response_model
async def get_wishlist(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Hitung total item wishlist user yang belum dihapus
    total_result = await db.execute(
        select(func.count()).select_from(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.is_deleted == False
        )
    )
    total = total_result.scalar()

    # Ambil item wishlist user
    result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.is_deleted == False
        )
        .offset((page - 1) * limit)
        .limit(limit)
    )
    wishlist_items = result.scalars().all()

    # Bangun response dengan detail produk (filter produk yang sudah dihapus)
    response_items = []
    for item in wishlist_items:
        product_result = await db.execute(
            select(Product).where(
                Product.id == item.product_id,
                Product.is_deleted == False
            )
        )
        product = product_result.scalar_one_or_none()
        if product:
            response_items.append({
                "id": item.id,
                "user_id": item.user_id,
                "product_id": item.product_id,
                "product_name": product.product_name,
                "product_price": product.price,
                "product_image_url": product.image_url,
                "created_at": item.created_at
            })

    return paginated_response(response_items, page, limit, total)

@router.post("/", response_model=WishlistResponse, status_code=201)
async def add_to_wishlist(
    wishlist_item: WishlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek apakah produk ada dan belum dihapus
    product_result = await db.execute(
        select(Product).where(
            Product.id == wishlist_item.product_id,
            Product.is_deleted == False
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Cek apakah produk sudah ada di wishlist user
    existing_result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.product_id == wishlist_item.product_id,
            Wishlist.is_deleted == False
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Product already in wishlist")

    # Tambahkan ke wishlist
    db_wishlist = Wishlist(
        user_id=current_user.id,
        product_id=wishlist_item.product_id
    )
    db.add(db_wishlist)
    await db.commit()
    await db.refresh(db_wishlist)

    return {
        "id": db_wishlist.id,
        "user_id": db_wishlist.user_id,
        "product_id": db_wishlist.product_id,
        "product_name": product.product_name,
        "product_price": product.price,
        "product_image_url": product.image_url,
        "created_at": db_wishlist.created_at
    }

@router.delete("/{product_id}", status_code=204)
async def remove_from_wishlist(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Soft delete item wishlist berdasarkan product_id
    result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.product_id == product_id,
            Wishlist.is_deleted == False
        )
    )
    wishlist_item = result.scalar_one_or_none()
    if not wishlist_item:
        raise HTTPException(status_code=404, detail=f"Wishlist item with product_id {product_id} not found")

    wishlist_item.is_deleted = True
    wishlist_item.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return None