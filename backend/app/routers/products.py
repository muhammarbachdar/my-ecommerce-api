from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductResponse
from app.core.security import require_admin
from app.models import User
from app.utils.uploader import upload_image

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

# Get all products with search & filter (hanya yang belum di-soft delete)
@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Product).where(Product.is_deleted == False)
    
    # Search by product_name (case insensitive)
    if q:
        query = query.where(Product.product_name.ilike(f"%{q}%"))
    
    # Filter by category
    if category_id:
        query = query.where(Product.category_id == category_id)
    
    # Filter by price range
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    
    result = await db.execute(
        query.offset(skip).limit(limit).order_by(Product.id)
    )
    products = result.scalars().all()
    return products

# Get product by id (hanya yang belum di-soft delete)
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
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
    
    product.is_deleted = True
    await db.commit()
    return None

# Upload product image (admin only)
@router.post("/upload-image", status_code=201)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    url = await upload_image(file)
    return {"image_url": url}