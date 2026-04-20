from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models import Order, OrderItem, Cart, Product, User
from app.schemas import OrderCreate, OrderResponse, OrderItemResponse
from app.core.security import get_current_user, require_admin
from app.utils.pagination import paginated_response

router = APIRouter(prefix="/orders", tags=["orders"])

# Helper function to get user orders (used by users.py)
async def get_user_orders(
    user_id: int,
    page: int,
    limit: int,
    db: AsyncSession
):
    # Hitung total
    total_result = await db.execute(
        select(func.count()).select_from(Order).where(Order.user_id == user_id)
    )
    total = total_result.scalar()
    
    # Ambil orders dengan eager loading (selectinload)
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.user_id == user_id)
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    
    # Build response (langsung akses item.product tanpa query tambahan)
    response_orders = []
    for order in orders:
        items_response = []
        for item in order.items:
            items_response.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.product_name if item.product else "Unknown",
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
                "created_at": item.created_at
            })
        
        response_orders.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
            "items": items_response
        })
    
    return paginated_response(response_orders, page, limit, total)

# ==================== ORDER ENDPOINTS ====================

@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's cart items
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id)
    )
    cart_items = cart_result.scalars().all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Prepare order items data
    order_items_data = []
    total_price = 0
    
    # Mulai transaction
    async with db.begin():
        for item in cart_items:
            product_result = await db.execute(
                select(Product).where(
                    Product.id == item.product_id,
                    Product.is_deleted == False
                )
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found or has been deleted")
            
            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.product_name}")
            
            # Kurangi stok (di dalam transaction)
            product.stock -= item.quantity
            
            subtotal = product.price * item.quantity
            total_price += subtotal
            
            order_items_data.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price_at_purchase": product.price
            })
        
        # Create order
        db_order = Order(
            user_id=current_user.id,
            total_price=total_price,
            status="pending",
            shipping_address=order_data.shipping_address if order_data else None
        )
        db.add(db_order)
        await db.flush()  # Get order.id
        
        # Create order items
        for item_data in order_items_data:
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                price_at_purchase=item_data["price_at_purchase"]
            )
            db.add(db_item)
        
        # Clear user's cart
        for item in cart_items:
            await db.delete(item)
        
        # Commit otomatis di sini (keluar dari async with)
    
    await db.refresh(db_order)
    return db_order

# Get current user orders
@router.get("/me", response_model=dict)
async def get_my_orders(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_orders(current_user.id, page, limit, db)

# Get order by id (user can only see their own)
@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build response langsung dari eager loading
    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else "Unknown",
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "subtotal": item.price_at_purchase * item.quantity,
            "created_at": item.created_at
        })
    
    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": order.total_price,
        "status": order.status,
        "created_at": order.created_at,
        "items": items_response
    }

# ==================== ADMIN ENDPOINTS ====================

# Get all orders (admin only)
@router.get("/", response_model=dict)
async def get_all_orders(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    total_result = await db.execute(select(func.count()).select_from(Order))
    total = total_result.scalar()
    
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    
    # Build response untuk admin
    response_orders = []
    for order in orders:
        items_response = []
        for item in order.items:
            items_response.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.product_name if item.product else "Unknown",
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
                "created_at": item.created_at
            })
        
        response_orders.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
            "items": items_response
        })
    
    return paginated_response(response_orders, page, limit, total)

# Update order status (admin only)
@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    valid_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order