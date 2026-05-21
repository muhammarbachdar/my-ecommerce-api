# orders.py (LENGKAP - DENGAN PERBAIKAN BUG begin_nested & DEAD CODE)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models import Order, OrderItem, Cart, Product, User, Payment, Voucher, VoucherUsage
from app.schemas import OrderCreate, OrderResponse, OrderItemResponse, OrderWithPaymentResponse
from app.core.security import get_current_user, require_admin
from app.utils.pagination import paginated_response
from app.core.enums import OrderStatus
from app.services.xendit_service import xendit_service

router = APIRouter(tags=["orders"])

# ==================== HELPER FUNCTIONS ====================

async def get_user_orders(
    user_id: int,
    page: int,
    limit: int,
    db: AsyncSession
):
    # Helper: hitung total pesanan user
    total_result = await db.execute(
        select(func.count()).select_from(Order).where(Order.user_id == user_id, Order.is_deleted == False)
    )
    total = total_result.scalar()

    # Helper: ambil pesanan user dengan item dan produk terkait
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.user_id == user_id, Order.is_deleted == False)
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    # Helper: format response pesanan user
    response_orders = []
    for order in orders:
        items_response = []
        for item in order.items:
            items_response.append({
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_name": item.product.product_name if item.product else "Unknown",
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
                "created_at": item.created_at
            })

        total_val = float(order.total_price or 0.0)
        discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
        final_price_val = max(0.0, total_val - discount_val)

        response_orders.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_price": total_val,
            "discount_amount": discount_val,
            "final_price": final_price_val,
            "status": order.status,
            "created_at": order.created_at,
            "shipping_address": order.shipping_address,
            "items": items_response
        })

    return paginated_response(response_orders, page, limit, total)


# ==================== ENDPOINTS ====================

@router.post("/", response_model=OrderWithPaymentResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ambil semua item keranjang user yang belum dihapus (dengan row lock untuk race condition)
    cart_result = await db.execute(
        select(Cart).where(
            Cart.user_id == current_user.id,
            Cart.is_deleted == False
        ).with_for_update()
    )
    all_cart_items = cart_result.scalars().all()

    if not all_cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Filter item keranjang yang dipilih untuk checkout
    selected_cart_item_ids = set(order_data.cart_item_ids)
    cart_items_to_process = [item for item in all_cart_items if item.id in selected_cart_item_ids]

    if not cart_items_to_process:
        raise HTTPException(status_code=400, detail="No items selected for checkout")

    # Proses setiap item: validasi stok dan kurangi stok produk
    order_items_data = []
    total_price = 0

    for item in cart_items_to_process:
        product_result = await db.execute(
            select(Product).where(
                Product.id == item.product_id,
                Product.is_deleted == False
            ).with_for_update()
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} not found or has been deleted"
            )
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product {product.product_name}"
            )

        product.stock -= item.quantity
        subtotal = product.price * item.quantity
        total_price += subtotal
        order_items_data.append({
            "cart_item_id": item.id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price_at_purchase": product.price,
            "product_name": product.product_name
        })

    voucher = None
    discount_amount = Decimal('0')
    if order_data.voucher_code:
        now = datetime.now(timezone.utc)
        voucher_result = await db.execute(
            select(Voucher).where(
                Voucher.code == order_data.voucher_code.upper(),
                Voucher.is_active == True,
                Voucher.start_date <= now,
                Voucher.end_date >= now,
                Voucher.used_count < Voucher.usage_limit
            ).with_for_update()
        )
        voucher = voucher_result.scalar_one_or_none()
        if not voucher:
            raise HTTPException(status_code=400, detail="Invalid or expired voucher code")

        if total_price < voucher.min_purchase:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum purchase Rp{int(voucher.min_purchase):,} required"
            )

        user_usage_result = await db.execute(
            select(func.count()).select_from(VoucherUsage).where(
                VoucherUsage.user_id == current_user.id,
                VoucherUsage.voucher_id == voucher.id
            )
        )
        used_by_user = user_usage_result.scalar() or 0
        if used_by_user >= voucher.usage_per_user:
            raise HTTPException(status_code=400, detail="Voucher usage limit reached for this user")

        if voucher.discount_type == "percentage":
            discount_amount = total_price * Decimal(str(voucher.discount_value)) / 100
            if voucher.max_discount and discount_amount > Decimal(str(voucher.max_discount)):
                discount_amount = Decimal(str(voucher.max_discount))
        else:
            discount_amount = min(Decimal(str(voucher.discount_value)), total_price)

    db_order = Order(
        user_id=current_user.id,
        total_price=total_price,
        status="pending",
        shipping_address=order_data.shipping_address if order_data else None
    )
    if voucher:
        db_order.applied_voucher_id = voucher.id
        db_order.discount_amount = discount_amount

    db.add(db_order)
    await db.flush()

    for item_data in order_items_data:
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            price_at_purchase=item_data["price_at_purchase"]
        )
        db.add(db_item)

    for item in cart_items_to_process:
        await db.delete(item)

    await db.commit()
    await db.refresh(db_order)

    final_amount = total_price - discount_amount
    if final_amount < 0:
        final_amount = 0.0

    external_id = f"ORDER-{db_order.id}"

    try:
        invoice_data = await xendit_service.create_invoice(
            external_id=external_id,
            amount=final_amount,
            payer_email=current_user.email,
            description=f"Payment for order #{db_order.id}"
        )
    except HTTPException as e:
        for item_data in order_items_data:
            product_result = await db.execute(
                select(Product).where(Product.id == item_data["product_id"]).with_for_update()
            )
            product = product_result.scalar_one_or_none()
            if product:
                product.stock += item_data["quantity"]
        db_order.status = "cancelled"
        if voucher:
            db_order.applied_voucher_id = None
            db_order.discount_amount = Decimal('0')
            if voucher.used_count > 0:
                voucher.used_count -= 1
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create Xendit invoice: {e.detail}"
        )

    db_payment = Payment(
        order_id=db_order.id,
        method="xendit",
        amount=final_amount,
        status="pending",
        payment_url=invoice_data.get("invoice_url"),
        xendit_invoice_id=invoice_data.get("id"),
        invoice_url=invoice_data.get("invoice_url")
    )
    db.add(db_payment)
    await db.commit()

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == db_order.id)
    )
    order = result.scalar_one()

    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else "Unknown",
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "subtotal": item.price_at_purchase * item.quantity,
            "created_at": item.created_at
        })

    total_val = float(order.total_price or 0.0)
    discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
    final_price_val = max(0.0, total_val - discount_val)

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": total_val,
        "discount_amount": discount_val,
        "final_price": final_price_val,
        "status": order.status,
        "created_at": order.created_at,
        "shipping_address": order.shipping_address,
        "items": items_response,
        "invoice_url": db_payment.invoice_url
    }


@router.get("/me", response_model=dict)
async def get_my_orders(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_orders(current_user.id, page, limit, db)


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

    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else "Unknown",
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "subtotal": item.price_at_purchase * item.quantity,
            "created_at": item.created_at
        })

    total_val = float(order.total_price or 0.0)
    discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
    final_price_val = max(0.0, total_val - discount_val)

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": total_val,
        "discount_amount": discount_val,
        "final_price": final_price_val,
        "status": order.status,
        "created_at": order.created_at,
        "shipping_address": order.shipping_address,
        "items": items_response
    }


@router.get("/", response_model=dict)
async def get_all_orders(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    total_result = await db.execute(
        select(func.count()).select_from(Order).where(Order.is_deleted == False)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.is_deleted == False)
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    response_orders = []
    for order in orders:
        items_response = []
        for item in order.items:
            items_response.append({
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_name": item.product.product_name if item.product else "Unknown",
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
                "created_at": item.created_at
            })

        total_val = float(order.total_price or 0.0)
        discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
        final_price_val = max(0.0, total_val - discount_val)

        response_orders.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_price": total_val,
            "discount_amount": discount_val,
            "final_price": final_price_val,
            "status": order.status,
            "created_at": order.created_at,
            "shipping_address": order.shipping_address,
            "items": items_response
        })

    return paginated_response(response_orders, page, limit, total)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    try:
        status_enum = OrderStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}")

    ALLOWED_TRANSITIONS = {
        "pending": ["paid", "cancelled"],
        "paid": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": [],
        "cancelled": []
    }

    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    old_status = order.status

    if status == "cancelled" and old_status == "cancelled":
        await db.refresh(order, attribute_names=["items"])
        items_response = []
        for item in order.items:
            items_response.append({
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_name": item.product.product_name if item.product else "Unknown",
                "quantity": item.quantity,
                "price_at_purchase": item.price_at_purchase,
                "subtotal": item.price_at_purchase * item.quantity,
                "created_at": item.created_at
            })
        total_val = float(order.total_price or 0.0)
        discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
        final_price_val = max(0.0, total_val - discount_val)
        return {
            "id": order.id,
            "user_id": order.user_id,
            "total_price": total_val,
            "discount_amount": discount_val,
            "final_price": final_price_val,
            "status": order.status,
            "created_at": order.created_at,
            "shipping_address": order.shipping_address,
            "items": items_response
        }

    if status not in ALLOWED_TRANSITIONS.get(old_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{old_status}' to '{status}'"
        )

    if status in ["shipped", "delivered"]:
        payment_result = await db.execute(
            select(Payment).where(Payment.order_id == order.id)
        )
        payment = payment_result.scalar_one_or_none()
        if not payment or payment.status != "paid":
            raise HTTPException(
                status_code=400,
                detail="Cannot change status to shipped/delivered because payment is not confirmed"
            )

    if status == "cancelled" and old_status != "cancelled":
        for item in order.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalar_one_or_none()
            if product:
                product.stock += item.quantity

        if order.applied_voucher_id is not None:
            voucher_result = await db.execute(
                select(Voucher).where(Voucher.id == order.applied_voucher_id).with_for_update()
            )
            voucher = voucher_result.scalar_one_or_none()
            if voucher and voucher.used_count > 0:
                voucher.used_count -= 1
            order.applied_voucher_id = None
            order.discount_amount = Decimal('0')

    order.status = status
    await db.commit()
    await db.refresh(order)

    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else "Unknown",
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "subtotal": item.price_at_purchase * item.quantity,
            "created_at": item.created_at
        })

    total_val = float(order.total_price or 0.0)
    discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
    final_price_val = max(0.0, total_val - discount_val)

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": total_val,
        "discount_amount": discount_val,
        "final_price": final_price_val,
        "status": order.status,
        "created_at": order.created_at,
        "shipping_address": order.shipping_address,
        "items": items_response
    }


@router.patch("/{order_id}/user-cancel", response_model=OrderResponse)
async def user_cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
        .with_for_update()
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")

    for item in order.items:
        product_result = await db.execute(
            select(Product).where(Product.id == item.product_id).with_for_update()
        )
        product = product_result.scalar_one_or_none()
        if product:
            product.stock += item.quantity

    if order.applied_voucher_id is not None:
        voucher_result = await db.execute(
            select(Voucher).where(Voucher.id == order.applied_voucher_id).with_for_update()
        )
        voucher = voucher_result.scalar_one_or_none()
        if voucher and voucher.used_count > 0:
            voucher.used_count -= 1
        order.applied_voucher_id = None
        order.discount_amount = Decimal('0')

    order.status = "cancelled"
    await db.commit()
    await db.refresh(order)

    items_response = []
    for item in order.items:
        items_response.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else "Unknown",
            "quantity": item.quantity,
            "price_at_purchase": item.price_at_purchase,
            "subtotal": item.price_at_purchase * item.quantity,
            "created_at": item.created_at
        })

    total_val = float(order.total_price or 0.0)
    discount_val = float(order.discount_amount if order.discount_amount is not None else 0.0)
    final_price_val = max(0.0, total_val - discount_val)

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_price": total_val,
        "discount_amount": discount_val,
        "final_price": final_price_val,
        "status": order.status,
        "created_at": order.created_at,
        "shipping_address": order.shipping_address,
        "items": items_response
    }


# ==================== BACKGROUND TASK ====================

async def auto_cancel_expired_orders(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.status == "pending",
            Order.created_at < cutoff,
            Order.is_deleted == False
        )
    )
    orders = result.scalars().all()
    if not orders:
        return 0

    for order in orders:
        for item in order.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalar_one_or_none()
            if product:
                product.stock += item.quantity

        if order.applied_voucher_id is not None:
            voucher_result = await db.execute(
                select(Voucher).where(Voucher.id == order.applied_voucher_id).with_for_update()
            )
            voucher = voucher_result.scalar_one_or_none()
            if voucher and voucher.used_count > 0:
                voucher.used_count -= 1
            order.applied_voucher_id = None
            order.discount_amount = Decimal('0')

        order.status = "cancelled"

    await db.commit()
    return len(orders)