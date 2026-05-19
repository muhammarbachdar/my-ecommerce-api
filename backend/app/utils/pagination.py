# === FILE: app/utils/pagination.py ===
import math
from typing import TypeVar, List, Any
from pydantic import BaseModel

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 10

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

class PaginationMeta(BaseModel):
    current_page: int
    per_page: int
    total_data: int
    total_pages: int
    next_page: int | None
    prev_page: int | None

def paginate(page: int, limit: int, total: int) -> PaginationMeta:
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    return PaginationMeta(
        current_page=page,
        per_page=limit,
        total_data=total,
        total_pages=total_pages,
        next_page=page + 1 if page < total_pages else None,
        prev_page=page - 1 if page > 1 else None
    )

def paginated_response(data: List[Any], page: int, limit: int, total: int) -> dict:
    # [FIX] Batasi limit maksimal 100 untuk mencegah DoS
    limit = min(limit, 100)
    """
    Mengkonversi objek SQLAlchemy ke dict jika memiliki method `__dict__` atau `to_dict`,
    namun tetap aman untuk data yang sudah berupa dict.
    """
    serialized_data = []
    for item in data:
        if hasattr(item, "model_dump"):      # Pydantic model
            serialized_data.append(item.model_dump())
        elif hasattr(item, "__dict__"):      # SQLAlchemy model biasa
            # Hindari atribut internal SQLAlchemy
            item_dict = {c.key: getattr(item, c.key) for c in item.__table__.columns}
            serialized_data.append(item_dict)
        else:
            serialized_data.append(item)     # sudah dict atau tipe lain
    
    return {
        "status": "success",
        "data": serialized_data,
        "pagination": paginate(page, limit, total).model_dump()
    }