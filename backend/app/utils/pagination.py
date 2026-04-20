import math
from typing import TypeVar, Generic, List
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

class PaginatedResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: List[T]
    pagination: PaginationMeta

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

def paginated_response(data: List, page: int, limit: int, total: int) -> dict:
    return {
        "status": "success",
        "data": data,
        "pagination": paginate(page, limit, total).model_dump()
    }