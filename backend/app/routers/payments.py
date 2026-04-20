from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models import Payment, Order, User
from app.schemas import PaymentCreate, PaymentResponse
from app.core.security import get_current_user, require_admin
import uuid

router = APIRouter(prefix="/payments", tags=["payments"])

# Create payment (mock) - user checkout
@router.post("/", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cek apakah order ada dan milik user
    order_result = await db.execute(
        select(Order).where(
            Order.id == payment_data.order_id,
            Order.user_id == current_user.id
        )
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Cek apakah sudah ada payment untuk order ini
    existing_result = await db.execute(
        select(Payment).where(Payment.order_id == payment_data.order_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Payment already exists for this order")
    
    # Generate mock payment URL
    mock_payment_url = f"https://mock-payment.example.com/pay/{uuid.uuid4().hex}"
    
    db_payment = Payment(
        order_id=payment_data.order_id,
        method=payment_data.method,
        amount=order.total_price,
        status="pending",
        payment_url=mock_payment_url
    )
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return db_payment

# Get payment by order id
@router.get("/order/{order_id}", response_model=PaymentResponse)
async def get_payment_by_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Payment).where(Payment.order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Cek apakah order milik user atau user adalah admin
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return payment

# Confirm payment (mock) - simulate payment success (admin only)
@router.patch("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="Payment already confirmed")
    
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    
    # Update order status to paid
    order_result = await db.execute(select(Order).where(Order.id == payment.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "paid"
    
    await db.commit()
    await db.refresh(payment)
    return payment