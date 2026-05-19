# === FILE: app/routers/carts.py ===
# carts.py (LENGKAP - hanya update_cart_item yang berubah)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.database import get_db
from app.models import Cart, Product, User
from app.schemas import CartCreate, CartUpdate, CartResponse
from app.core.security import get_current_user
from app.utils.pagination import paginated_response
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["carts"])

@router.get("/", response_model=dict)
async def get_cart(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Hitung total item keranjang user yang belum dihapus
    total_result = await db.execute(
        select(func.count()).select_from(Cart).where(
            Cart.user_id == current_user.id,
            Cart.is_deleted == False
        )
    )
    total = total_result.scalar()

    # Ambil item keranjang user dengan data produk terkait
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.product))
        .where(
            Cart.user_id == current_user.id,
            Cart.is_deleted == False
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Cart.created_at.desc())
    )
    cart_items = result.scalars().all()

    # Bangun response dengan subtotal, filter produk yang sudah dihapus
    response_items = []
    for item in cart_items:
        product = item.product
        if not product or product.is_deleted:
            continue
        response_items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.product_name,
            "price": product.price,
            "quantity": item.quantity,
            "subtotal": product.price * item.quantity,
            "product_image_url": product.image_url,
            "created_at": item.created_at
        })

    return paginated_response(response_items, page, limit, total)

@router.post("/", response_model=CartResponse, status_code=201)
async def add_to_cart(
    cart_item: CartCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Pastikan produk tersedia dan belum dihapus
    product_result = await db.execute(
        select(Product).where(
            Product.id == cart_item.product_id,
            Product.is_deleted == False
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

    # Cek stok produk
    if product.stock < cart_item.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Stok tidak mencukupi. Tersedia: {product.stock}"
        )

    # Cek apakah produk sudah ada di keranjang user
    existing_result = await db.execute(
        select(Cart).where(
            Cart.user_id == current_user.id,
            Cart.product_id == cart_item.product_id,
            Cart.is_deleted == False
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Jika sudah ada, update quantity
        new_quantity = existing.quantity + cart_item.quantity
        if product.stock < new_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Tidak dapat menambah {cart_item.quantity}. Maksimal tersedia: {product.stock - existing.quantity}"
            )
        existing.quantity = new_quantity
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Jika belum ada, buat item baru
        db_cart = Cart(
            user_id=current_user.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity
        )
        db.add(db_cart)
        await db.commit()
        await db.refresh(db_cart)
        return db_cart

@router.put("/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: int,
    cart_update: CartUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validasi jumlah minimal 1
    if cart_update.quantity < 1:
        raise HTTPException(status_code=400, detail="Jumlah minimal adalah 1")

    # Cari item keranjang milik user
    result = await db.execute(
        select(Cart).where(
            Cart.id == item_id,
            Cart.user_id == current_user.id,
            Cart.is_deleted == False
        )
    )
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item keranjang tidak ditemukan")

    # Cek stok produk sebelum update
    # [FIX] Tambah .with_for_update() untuk mencegah race condition update stok bersamaan
    product_result = await db.execute(
        select(Product).where(Product.id == cart_item.product_id).with_for_update()
    )
    product = product_result.scalar_one_or_none()
    # [FIX] Guard clause untuk produk yang sudah di-soft-delete
    if not product or product.is_deleted:
        raise HTTPException(status_code=400, detail="Produk sudah tidak tersedia atau telah dihapus")
    if product and product.stock < cart_update.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Stok tidak mencukupi. Tersedia: {product.stock}"
        )

    # Update quantity
    cart_item.quantity = cart_update.quantity
    await db.commit()
    await db.refresh(cart_item)
    return cart_item

@router.delete("/{item_id}", status_code=204)
async def remove_from_cart(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cari item keranjang milik user
    result = await db.execute(
        select(Cart).where(
            Cart.id == item_id,
            Cart.user_id == current_user.id,
            Cart.is_deleted == False
        )
    )
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item keranjang tidak ditemukan")

    # Hapus permanen item keranjang
    await db.delete(cart_item)
    await db.commit()
    return None