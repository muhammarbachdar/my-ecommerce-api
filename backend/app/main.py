# main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import time

from app.routers import auth, products, categories, carts, users, orders, payments, wishlist, reviews, vouchers, addresses, admin
from app.middleware.request_id import RequestIDMiddleware
from app.database import get_db, engine   # FIX: import engine
from app.core.limiter import limiter, setup_rate_limit
from app.core.logging import setup_logging
from app.core.config import settings

logger = setup_logging()

app = FastAPI(
    title="E-commerce API",
    version="1.0.0",
    redirect_slashes=False
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Catat waktu dan log setiap request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        return response

app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_rate_limit(app)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(products.router, prefix="/api/v1/products")
app.include_router(categories.router, prefix="/api/v1/categories")
app.include_router(carts.router, prefix="/api/v1/carts")
app.include_router(users.router, prefix="/api/v1/users")
app.include_router(orders.router, prefix="/api/v1/orders")
app.include_router(payments.router, prefix="/api/v1/payments")
app.include_router(wishlist.router, prefix="/api/v1/wishlist")
app.include_router(reviews.router, prefix="/api/v1/reviews")
app.include_router(vouchers.router, prefix="/api/v1/vouchers")
app.include_router(addresses.router, prefix="/api/v1/addresses")
app.include_router(admin.router, prefix="/api/v1/admin")

@app.get("/")
async def root():
    return {"message": "E-commerce API is running"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Cek koneksi database dan redis untuk health check
    try:
        await db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"

    redis_status = "up"

    if db_status == "down":
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": db_status})
    return {"status": "healthy", "database": db_status, "redis": redis_status}

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    # Log error HTTP dengan request_id
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - request_id: {getattr(request.state, 'request_id', 'N/A')}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": getattr(request.state, 'request_id', None)}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    # Tangani error tak terduga dan log dengan stack trace
    logger.exception(f"Unhandled exception: {exc} - request_id: {getattr(request.state, 'request_id', 'N/A')}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": getattr(request.state, 'request_id', None)}
    )

# FIX: graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    # Tutup koneksi database dengan rapi saat aplikasi mati
    logger.info("Shutting down, closing database connection pool...")
    await engine.dispose()
    logger.info("Database connections closed.")