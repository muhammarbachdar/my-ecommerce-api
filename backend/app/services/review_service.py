# review_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Review, Product

async def update_product_rating(db: AsyncSession, product_id: int):
    """Hitung ulang rata-rata rating dan total review untuk suatu produk"""
    # Hitung rata-rata rating dan jumlah review aktif
    result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.product_id == product_id, Review.is_deleted == False)
    )
    avg_rating, total_reviews = result.first()
    
    # Update produk
    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if product:
        product.average_rating = round(float(avg_rating), 2) if avg_rating else 0.0
        product.total_reviews = total_reviews or 0
        await db.flush()  # tidak perlu commit, nanti commit di luar