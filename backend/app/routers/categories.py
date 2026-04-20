from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.database import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryResponse
from app.core.security import require_admin
from app.models import User
from app.utils.pagination import paginated_response

router = APIRouter(prefix="/categories", tags=["categories"])

# ==================== PUBLIC ENDPOINTS ====================

@router.get("/", response_model=dict)
async def get_all_categories(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    total_result = await db.execute(
        select(func.count()).select_from(Category).where(Category.is_deleted == False)
    )
    total = total_result.scalar()
    
    result = await db.execute(
        select(Category)
        .where(Category.is_deleted == False)
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Category.name)
    )
    categories = result.scalars().all()
    
    return paginated_response(categories, page, limit, total)

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.is_deleted == False
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category

# ==================== ADMIN ONLY ENDPOINTS ====================

@router.post("/admin/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Cek slug duplikat (hanya dari kategori yang belum dihapus)
    result = await db.execute(
        select(Category).where(
            Category.slug == category.slug,
            Category.is_deleted == False
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    db_category = Category(
        name=category.name,
        slug=category.slug
    )
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

@router.put("/admin/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.is_deleted == False
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Cek slug duplikat (kecuali untuk dirinya sendiri, dan hanya dari kategori yang belum dihapus)
    if category_update.slug != category.slug:
        dup_result = await db.execute(
            select(Category).where(
                Category.slug == category_update.slug,
                Category.id != category_id,
                Category.is_deleted == False
            )
        )
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists"
            )
    
    category.name = category_update.name
    category.slug = category_update.slug
    
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/admin/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.is_deleted == False
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    category.is_deleted = True
    await db.commit()
    return None