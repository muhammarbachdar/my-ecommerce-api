from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductResponse
from app.core.security import require_admin
from app.models import User

router = APIRouter(prefix="/products", tags=["products"])

# Create product (admin only)
@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    db_product = Product(
        product_name=product.product_name,
        price=product.price,
        stock=product.stock,
        image_url=product.image_url,
        description=product.description
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

# Get all products (hanya yang belum di-soft delete)
@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    result = await db.execute(
        select(Product)
        .where(Product.is_deleted == False)
        .offset(skip)
        .limit(limit)
    )
    products = result.scalars().all()
    return products

# Get product by id (hanya yang belum di-soft delete)
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product

# Update product (hanya yang belum di-soft delete)
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from sqlalchemy import select
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.product_name = product_update.product_name
    product.price = product_update.price
    product.stock = product_update.stock
    product.image_url = product_update.image_url
    product.description = product_update.description
    
    await db.commit()
    await db.refresh(product)
    return product

# Delete product (soft delete)
@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from sqlalchemy import select
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Soft delete
    product.is_deleted = True
    await db.commit()
    return None