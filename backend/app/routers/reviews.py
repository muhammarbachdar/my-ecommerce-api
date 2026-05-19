# reviews.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import Review, Product, Order, OrderItem, User
from app.schemas import ReviewCreate, ReviewUpdate, ReviewResponse
from app.core.security import get_current_user, require_admin

router = APIRouter(tags=["reviews"])

async def update_product_rating(db: AsyncSession, product_id: int):
    """Hitung ulang average_rating dan total_reviews untuk suatu produk"""
    # Hitung rata-rata rating dan total review produk
    result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.product_id == product_id, Review.is_deleted == False)
    )
    avg_rating, total_reviews = result.first()
    
    # Update field rating di tabel produk
    await db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(
            average_rating=round(float(avg_rating), 1) if avg_rating else 0.0,
            total_reviews=total_reviews or 0
        )
    )
# ==================== USER ENDPOINTS ====================

# Get reviews for a product
@router.get("/product/{product_id}", response_model=List[ReviewResponse])
async def get_product_reviews(
    product_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    # Cek produk ada
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Ambil reviews produk
    result = await db.execute(
        select(Review)
        .where(Review.product_id == product_id, Review.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    
    # Ambil nama user untuk setiap review
    response_reviews = []
    for review in reviews:
        user_result = await db.execute(
            select(User).where(User.id == review.user_id)
        )
        user = user_result.scalar_one_or_none()
        response_reviews.append({
            "id": review.id,
            "user_id": review.user_id,
            "user_name": user.email.split('@')[0] if user else "Unknown",
            "product_id": review.product_id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
            "updated_at": review.updated_at
        })
    
    return response_reviews

# Get product average rating
@router.get("/product/{product_id}/average")
async def get_product_average_rating(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Hitung rata-rata rating langsung dari review
    result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.product_id == product_id, Review.is_deleted == False)
    )
    avg_rating, total_reviews = result.first()
    
    return {
        "product_id": product_id,
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
        "total_reviews": total_reviews or 0
    }

# Create review (user must have purchased the product)
@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek apakah user pernah membeli produk ini (hanya order yang sudah dibayar)
    order_result = await db.execute(
        select(OrderItem).join(Order).where(
            Order.user_id == current_user.id,
            OrderItem.product_id == review_data.product_id,
            Order.status == "paid"
        )
    )
    has_purchased = order_result.scalar_one_or_none()
    if not has_purchased:
        raise HTTPException(
            status_code=403,
            detail="You can only review products you have purchased"
        )
    
    # Cek apakah user sudah pernah review produk ini
    existing_result = await db.execute(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.product_id == review_data.product_id,
            Review.is_deleted == False
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this product"
        )
    
    # Buat review baru
    db_review = Review(
        user_id=current_user.id,
        product_id=review_data.product_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(db_review)
    await db.flush()  # agar product_id tersedia
    await update_product_rating(db, review_data.product_id)
    await db.commit()
    
    return {
        "id": db_review.id,
        "user_id": db_review.user_id,
        "user_name": current_user.email.split('@')[0],
        "product_id": db_review.product_id,
        "rating": db_review.rating,
        "comment": db_review.comment,
        "created_at": db_review.created_at,
        "updated_at": db_review.updated_at
    }

# Update own review
@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cari review milik user
    result = await db.execute(
        select(Review).where(
            Review.id == review_id,
            Review.user_id == current_user.id,
            Review.is_deleted == False
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Update rating/komentar
    if review_update.rating is not None:
        review.rating = review_update.rating
    if review_update.comment is not None:
        review.comment = review_update.comment
    
    review.updated_at = datetime.now(timezone.utc)
    
# setelah update atribut review
    await db.flush()
    await update_product_rating(db, review.product_id)
    await db.commit()
    
    user_result = await db.execute(select(User).where(User.id == review.user_id))
    user = user_result.scalar_one_or_none()
    
    return {
        "id": review.id,
        "user_id": review.user_id,
        "user_name": user.email.split('@')[0] if user else "Unknown",
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at
    }

# Delete own review (soft delete)
@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Soft delete review milik user
    result = await db.execute(
        select(Review).where(
            Review.id == review_id,
            Review.user_id == current_user.id,
            Review.is_deleted == False
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_deleted = True
    await db.flush()
    await update_product_rating(db, review.product_id)
    await db.commit()

# ==================== ADMIN ENDPOINTS ====================

# Delete any review (admin only)
@router.delete("/admin/{review_id}", status_code=204)
async def admin_delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Admin: soft delete review siapa pun
    result = await db.execute(
        select(Review).where(
            Review.id == review_id,
            Review.is_deleted == False
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_deleted = True
    await db.flush()
    await update_product_rating(db, review.product_id)
    await db.commit()