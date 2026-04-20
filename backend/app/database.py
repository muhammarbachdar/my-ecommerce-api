from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Ambil DATABASE_URL dari settings
DATABASE_URL = settings.DATABASE_URL

# Paksa pakai asyncpg (bukan psycopg2)
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Buat engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=5,
    max_overflow=10
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class untuk models
class Base(DeclarativeBase):
    pass

# Dependency untuk mendapatkan session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session