# products.py

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_   # FIX: tambah func
from typing import List, Optional
from app.database import get_db
from app.models import Product, Category   # FIX: tambah Category
from app.schemas import ProductCreate, ProductResponse
from app.core.security import require_admin
from app.models import User
from app.utils.uploader import upload_image
from app.utils.pagination import paginated_response

router = APIRouter(tags=["products"])

# Create product (admin only)
@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Validasi kategori jika diberikan
    if product.category_id is not None:
        cat_result = await db.execute(
            select(Category).where(
                Category.id == product.category_id,
                Category.is_deleted == False
            )
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category not found or deleted")

    # Buat produk baru
    db_product = Product(
        product_name=product.product_name,
        price=product.price,
        stock=product.stock,
        image_url=product.image_url,
        description=product.description,
        category_id=product.category_id
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

# Get all products with search & filter
@router.get("/", response_model=dict)
async def get_all_products(
    page: int = 1,
    limit: int = 20,
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    # Bangun query total produk dengan filter
    total_query = select(func.count()).select_from(Product).where(Product.is_deleted == False)
    if q:
        total_query = total_query.where(Product.product_name.ilike(f"%{q}%"))
    if category_id:
        total_query = total_query.where(Product.category_id == category_id)
    if min_price is not None:
        total_query = total_query.where(Product.price >= min_price)
    if max_price is not None:
        total_query = total_query.where(Product.price <= max_price)

    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # Bangun query produk dengan filter yang sama
    query = select(Product).where(Product.is_deleted == False)
    if q:
        query = query.where(Product.product_name.ilike(f"%{q}%"))
    if category_id:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)

    offset = (page - 1) * limit
    result = await db.execute(
        query.offset(offset).limit(limit).order_by(Product.id)
    )
    products = result.scalars().all()

    product_schemas = [ProductResponse.model_validate(p) for p in products]
    return paginated_response(product_schemas, page, limit, total)

# Get product by id
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Ambil detail produk berdasarkan ID
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with id {product_id} not found"
        )
    return product

# Update product
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Cari produk yang akan diupdate
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with id {product_id} not found"
        )

    # Validasi kategori jika diubah
    if product_update.category_id is not None:
        cat_result = await db.execute(
            select(Category).where(
                Category.id == product_update.category_id,
                Category.is_deleted == False
            )
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category not found or deleted")

    # Update data produk
    product.product_name = product_update.product_name
    product.price = product_update.price
    product.stock = product_update.stock
    product.image_url = product_update.image_url
    product.description = product_update.description
    product.category_id = product_update.category_id

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
    # Soft delete produk
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
            detail=f"Product with id {product_id} not found"
        )

    product.is_deleted = True
    await db.commit()
    return None

# Upload product image
@router.post("/upload-image", status_code=201)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    # Upload gambar produk ke penyimpanan
    url = await upload_image(file)
    return {"image_url": url}