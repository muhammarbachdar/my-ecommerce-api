# payments.py (LENGKAP - hanya xendit_webhook yang berubah)

import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Payment, Order, User, Voucher, VoucherUsage, UserVoucher
from app.schemas import PaymentCreate, PaymentResponse
from app.core.security import get_current_user, require_admin
from app.core.config import settings
from app.services.xendit_service import xendit_service

router = APIRouter(tags=["payments"])

# ==================== ENDPOINT LAMA ====================

@router.post("/", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Membuat payment record secara manual (untuk metode pembayaran non-Xendit).
    """
    # Cek apakah order milik user dan masih ada
    order_result = await db.execute(
        select(Order).where(
            Order.id == payment_data.order_id,
            Order.user_id == current_user.id
        )
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Pastikan belum ada payment untuk order ini
    existing_result = await db.execute(
        select(Payment).where(Payment.order_id == payment_data.order_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Payment already exists for this order")

    # Buat URL pembayaran dummy (mock)
    mock_payment_url = f"https://mock-payment.example.com/pay/{uuid.uuid4().hex}"

    # Buat record payment
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


@router.get("/order/{order_id}", response_model=PaymentResponse)
async def get_payment_by_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan payment berdasarkan order_id.
    """
    # Cari payment berdasarkan order
    result = await db.execute(
        select(Payment).where(Payment.order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Validasi akses: hanya pemilik order atau admin
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    return payment


@router.patch("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    (Admin) Konfirmasi pembayaran secara manual, sekaligus mengaktifkan voucher jika ada.
    """
    # Row lock untuk payment dan order
    payment_result = await db.execute(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    )
    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="Payment already confirmed")

    # Lock order
    order_result = await db.execute(
        select(Order).where(Order.id == payment.order_id).with_for_update()
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not pending")

    # Jika order memiliki voucher applied, proses voucher
    if order.applied_voucher_id is not None:
        voucher_result = await db.execute(
            select(Voucher).where(Voucher.id == order.applied_voucher_id).with_for_update()
        )
        voucher = voucher_result.scalar_one_or_none()
        if not voucher:
            raise HTTPException(status_code=400, detail="Voucher not found")

        # Update used_count
        voucher.used_count += 1

        # Buat VoucherUsage record
        db_usage = VoucherUsage(
            voucher_id=voucher.id,
            user_id=order.user_id,
            order_id=order.id,
            discount_amount=order.discount_amount
        )
        db.add(db_usage)

        # Update user_voucher jika ada
        user_voucher_result = await db.execute(
            select(UserVoucher).where(
                UserVoucher.user_id == order.user_id,
                UserVoucher.voucher_id == voucher.id,
                UserVoucher.is_used == False
            )
        )
        user_voucher = user_voucher_result.scalar_one_or_none()
        if user_voucher:
            user_voucher.is_used = True
            user_voucher.used_at = datetime.now(timezone.utc)

    # Konfirmasi payment
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)

    # Update order status
    order.status = "paid"

    await db.commit()
    await db.refresh(payment)
    return payment


# ==================== WEBHOOK XENDIT ====================

@router.post("/xendit/webhook")
async def xendit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint webhook untuk menerima notifikasi dari Xendit setelah pembayaran.
    - Verifikasi token x-callback-token.
    - Hanya memproses event INVOICE.PAID.
    - Idempotent: jika payment sudah paid, langsung return.
    - Update status order dan payment, serta tandai voucher terpakai.
    - Stok produk tidak dikurangi karena sudah dilakukan saat checkout.
    """
    # 1. Verifikasi token
    callback_token = request.headers.get("x-callback-token")
    if not callback_token or not xendit_service.verify_webhook_token(callback_token):
        raise HTTPException(status_code=401, detail="Invalid callback token")

    # 2. Baca payload
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 3. Ekstrak data — Xendit kirim di root payload, bukan di dalam "data"
    invoice_id = payload.get("id")
    external_id = payload.get("external_id")
    status_xendit = payload.get("status")

    if status_xendit != "PAID":
        return {"status": "ignored", "reason": "not paid"}

    if not invoice_id or not external_id:
        raise HTTPException(status_code=400, detail="Missing invoice_id or external_id")

    # 4. Idempotency: cari payment berdasarkan xendit_invoice_id
    payment_result = await db.execute(
        select(Payment).where(Payment.xendit_invoice_id == invoice_id).with_for_update()
    )
    payment = payment_result.scalar_one_or_none()
    if not payment:
        # Invoice tidak ditemukan di sistem
        return {"status": "ignored", "reason": "payment record not found"}

    if payment.status == "paid":
        # Sudah diproses sebelumnya
        return {"status": "already_paid"}

    # [FIX] Validasi nominal pembayaran dari webhook
    webhook_amount = payload.get("amount")
    if webhook_amount is not None and float(webhook_amount) != float(payment.amount):
        # Log warning (cukup print) dan tolak webhook
        print(f"[WARNING] Xendit webhook amount mismatch: invoice {invoice_id}, expected {payment.amount}, got {webhook_amount}")
        return {"status": "amount_mismatch", "reason": f"Expected {payment.amount}, got {webhook_amount}"}

    # 5. Dapatkan order terkait
    order_result = await db.execute(
        select(Order).where(Order.id == payment.order_id).with_for_update()
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "paid":
        # Order sudah paid (mungkin duplikat webhook)
        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "already_paid"}

    # 6. Proses voucher jika ada
    if order.applied_voucher_id is not None:
        voucher_result = await db.execute(
            select(Voucher).where(Voucher.id == order.applied_voucher_id).with_for_update()
        )
        voucher = voucher_result.scalar_one_or_none()
        if voucher:
            # Tambah used_count
            voucher.used_count += 1

            # Buat VoucherUsage jika belum ada
            usage_result = await db.execute(
                select(VoucherUsage).where(VoucherUsage.order_id == order.id)
            )
            existing_usage = usage_result.scalar_one_or_none()
            if not existing_usage:
                db_usage = VoucherUsage(
                    voucher_id=voucher.id,
                    user_id=order.user_id,
                    order_id=order.id,
                    discount_amount=order.discount_amount
                )
                db.add(db_usage)

            # Update user_voucher
            user_voucher_result = await db.execute(
                select(UserVoucher).where(
                    UserVoucher.user_id == order.user_id,
                    UserVoucher.voucher_id == voucher.id,
                    UserVoucher.is_used == False
                )
            )
            user_voucher = user_voucher_result.scalar_one_or_none()
            if user_voucher:
                user_voucher.is_used = True
                user_voucher.used_at = datetime.now(timezone.utc)

    # 8. Ubah status
    order.status = "paid"
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)

    await db.commit()
    return {"status": "success"}