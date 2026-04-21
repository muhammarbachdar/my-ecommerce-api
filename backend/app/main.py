from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, products, categories, carts, users, orders, payments, wishlist, reviews, vouchers, addresses, admin

app = FastAPI(title="E-commerce API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # tambahkan domain production nanti
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(carts.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(wishlist.router)
app.include_router(reviews.router)
app.include_router(vouchers.router)
app.include_router(addresses.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "E-commerce API is running"}