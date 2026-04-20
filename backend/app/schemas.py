from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

# ==================== AUTH SCHEMAS ====================
class UserRegister(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_length(cls, v):
        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# ==================== USER SCHEMAS ====================
class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

# ==================== PRODUCT SCHEMAS ====================
class ProductBase(BaseModel):
    product_name: str
    price: float
    stock: int
    image_url: Optional[str] = None
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

# ==================== CATEGORY SCHEMAS ====================
class CategoryBase(BaseModel):
    name: str
    slug: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

# ==================== CART SCHEMAS ====================
class CartCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}

# ==================== ORDER SCHEMAS ====================
class OrderCreate(BaseModel):
    shipping_address: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price_at_purchase: float
    subtotal: float
    created_at: datetime

    model_config = {"from_attributes": True}

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_price: float
    status: str
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}