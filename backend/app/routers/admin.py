from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Order, OrderItem, Product, User
from app.core.security import require_admin
from app.models import User as UserModel

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    # 1. Total orders
    total_orders_result = await db.execute(
        select(func.count()).select_from(Order)
    )
    total_orders = total_orders_result.scalar() or 0
    
    # 2. Total revenue (dari order yang sudah paid)
    total_revenue_result = await db.execute(
        select(func.sum(Order.total_price)).where(Order.status == "paid")
    )
    total_revenue = total_revenue_result.scalar() or 0
    
    # 3. Orders by status
    statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    orders_by_status = {}
    for status in statuses:
        count_result = await db.execute(
            select(func.count()).select_from(Order).where(Order.status == status)
        )
        orders_by_status[status] = count_result.scalar() or 0
    
    # 4. Top 5 products
    top_products_result = await db.execute(
        select(
            Product.id,
            Product.product_name,
            func.sum(OrderItem.quantity).label("total_sold")
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status == "paid")
        .group_by(Product.id, Product.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_products = [
        {"id": row.id, "name": row.product_name, "total_sold": int(row.total_sold)}
        for row in top_products_result
    ]
    
    # 5. Revenue per month (last 6 months) - FIXED
    now = datetime.now(timezone.utc)
    revenue_by_month = []
    
    for i in range(5, -1, -1):
        # Hitung bulan target
        target_month = now.month - i
        target_year = now.year
        
        if target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # Start of month
        month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
        
        # End of month (start of next month)
        if target_month == 12:
            next_month_start = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month_start = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
        
        result = await db.execute(
            select(func.sum(Order.total_price))
            .where(
                Order.status == "paid",
                Order.created_at >= month_start,
                Order.created_at < next_month_start
            )
        )
        revenue = result.scalar() or 0
        
        revenue_by_month.append({
            "month": month_start.strftime("%B"),
            "revenue": float(revenue)
        })
    
    # 6. Total users
    total_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_deleted == False)
    )
    total_users = total_users_result.scalar() or 0
    
    return {
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "total_users": total_users,
        "orders_by_status": orders_by_status,
        "top_products": top_products,
        "revenue_by_month": revenue_by_month
    }