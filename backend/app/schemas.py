from pydantic import BaseModel, EmailStr, field_validator, Field
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
    name: Optional[str] = None
    phone: Optional[str] = None
    is_deleted: bool = False
    is_admin: bool = False

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

class PaymentCreate(BaseModel):
    order_id: int
    method: str  # bank_transfer, credit_card, ewallet

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    method: str
    amount: float
    status: str
    payment_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class WishlistCreate(BaseModel):
    product_id: int

class WishlistResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    product_name: str
    product_price: float
    product_image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)  # antara 1-5
    comment: Optional[str] = None

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    product_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class VoucherCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    discount_type: str  # percentage, fixed
    discount_value: float
    min_purchase: float = 0
    max_discount: Optional[float] = None
    usage_limit: int = 1
    usage_per_user: int = 1
    start_date: datetime
    end_date: datetime

class VoucherUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_purchase: Optional[float] = None
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class VoucherResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    min_purchase: float
    max_discount: Optional[float] = None
    usage_limit: int
    usage_per_user: int
    used_count: int
    start_date: datetime
    end_date: datetime
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class UserVoucherResponse(BaseModel):
    id: int
    voucher_id: int
    code: str
    name: str
    discount_type: str
    discount_value: float
    min_purchase: float
    max_discount: Optional[float] = None
    is_used: bool
    claimed_at: datetime
    used_at: Optional[datetime] = None

class ApplyVoucher(BaseModel):
    code: str
    order_id: int

class AddressCreate(BaseModel):
    label: str
    recipient_name: str
    phone: str
    full_address: str
    city: str
    province: str
    postal_code: str
    is_default: bool = False

class AddressUpdate(BaseModel):
    label: Optional[str] = None
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    full_address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    is_default: Optional[bool] = None

class AddressResponse(BaseModel):
    id: int
    user_id: int
    label: str
    recipient_name: str
    phone: str
    full_address: str
    city: str
    province: str
    postal_code: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}