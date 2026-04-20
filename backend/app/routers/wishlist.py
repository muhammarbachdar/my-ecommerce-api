from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List
from app.database import get_db
from app.models import Wishlist, Product, User
from app.schemas import WishlistCreate, WishlistResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

# Get current user's wishlist
@router.get("/", response_model=List[WishlistResponse])
async def get_wishlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Wishlist).where(Wishlist.user_id == current_user.id)
    )
    wishlist_items = result.scalars().all()
    
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
    
    return response_items

# Add product to wishlist
@router.post("/", response_model=WishlistResponse, status_code=201)
async def add_to_wishlist(
    wishlist_item: WishlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek apakah produk ada
    product_result = await db.execute(
        select(Product).where(
            Product.id == wishlist_item.product_id,
            Product.is_deleted == False
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Cek apakah sudah ada di wishlist
    existing_result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.product_id == wishlist_item.product_id
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Product already in wishlist")
    
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

# Remove product from wishlist
@router.delete("/{product_id}", status_code=204)
async def remove_from_wishlist(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == current_user.id,
            Wishlist.product_id == product_id
        )
    )
    wishlist_item = result.scalar_one_or_none()
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    
    await db.delete(wishlist_item)
    await db.commit()
    return None