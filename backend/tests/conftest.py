import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.main import app
from app.database import get_db, Base
from app.core.security import hash_password
from app.core.limiter import limiter
from app.models import User, Product, Category, Order, OrderItem, Cart

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

from app.core.limiter import limiter

@pytest.fixture(autouse=True, scope="function")
def disable_rate_limit():
    limiter._storage.reset()
    yield
    limiter._storage.reset()

@pytest.fixture(autouse=True, scope="function")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as client:
        yield client

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    user = User(
        email="test@example.com",
        hashed_password=hash_password("12345678"),
        name="Test User",
        phone="08123456789",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
async def test_admin(db_session: AsyncSession):
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        name="Admin",
        is_active=True,
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

@pytest.fixture(scope="function")
async def user_auth(client: AsyncClient, test_user):
    response = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "12345678"
    })
    return {
        "access_token": response.json()["access_token"],
        "refresh_token": response.json()["refresh_token"]
    }

@pytest.fixture(scope="function")
async def user_token(user_auth):
    return user_auth["access_token"]

@pytest.fixture(scope="function")
async def user_refresh_token(user_auth):
    return user_auth["refresh_token"]

@pytest.fixture(scope="function")
async def admin_auth(client: AsyncClient, test_admin):
    response = await client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "admin123"
    })
    return {
        "access_token": response.json()["access_token"],
        "refresh_token": response.json()["refresh_token"]
    }

@pytest.fixture(scope="function")
async def admin_token(admin_auth):
    return admin_auth["access_token"]

@pytest.fixture(scope="function")
async def test_product(db_session: AsyncSession):
    product = Product(
        product_name="Test Product",
        price=100000,
        stock=50,
        description="A test product",
        image_url="http://example.com/image.jpg"
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product

@pytest.fixture(scope="function")
async def test_category(db_session: AsyncSession):
    category = Category(name="Electronics", slug="electronics")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category

@pytest.fixture(scope="function")
async def test_order(db_session: AsyncSession, test_user, test_product):
    order = Order(
        user_id=test_user.id,
        total_price=200000,
        status="pending",
        shipping_address="Jl. Test No. 1"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    
    order_item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        quantity=2,
        price_at_purchase=100000
    )
    db_session.add(order_item)
    await db_session.commit()
    return order

@pytest.fixture(scope="function")
async def test_cart_item(db_session: AsyncSession, test_user, test_product):
    cart = Cart(
        user_id=test_user.id,
        product_id=test_product.id,
        quantity=1
    )
    db_session.add(cart)
    await db_session.commit()
    await db_session.refresh(cart)
    return cart