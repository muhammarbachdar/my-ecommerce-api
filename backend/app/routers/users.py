from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.database import get_db
from app.models import User, Order
from app.schemas import UserResponse, UserUpdate
from app.core.security import get_current_user, require_admin
from app.utils.pagination import paginated_response

router = APIRouter(tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.get("/me/orders", response_model=dict)
async def get_current_user_orders(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.routers.orders import get_user_orders
    return await get_user_orders(current_user.id, page, limit, db)

@router.get("/", response_model=dict)
async def get_all_users(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar()
    
    result = await db.execute(
        select(User)
        .offset((page - 1) * limit)
        .limit(limit)
        .order_by(User.id)
    )
    users = result.scalars().all()
    user_schemas = [UserResponse.model_validate(user) for user in users]
    return paginated_response(user_schemas, page, limit, total)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot ban yourself")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_deleted = not user.is_deleted
    await db.commit()
    await db.refresh(user)
    return user