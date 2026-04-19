from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase,  AsyncSession

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecommerce"
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    pool_size=5, 
    max_overflow=10)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session