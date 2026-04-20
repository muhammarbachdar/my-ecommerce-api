import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_review_requires_purchase(client: AsyncClient, user_token, test_product):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/reviews/", json={
        "product_id": test_product.id,
        "rating": 5,
        "comment": "Great product"
    }, headers=headers)
    assert response.status_code == 403  # Belum pernah beli

@pytest.mark.asyncio
async def test_create_review_after_purchase(client: AsyncClient, user_token, admin_token, test_order, test_product):
    headers_user = {"Authorization": f"Bearer {user_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    # Update order status ke paid
    await client.patch(f"/orders/{test_order.id}/status", params={"status": "paid"}, headers=headers_admin)
    
    response = await client.post("/reviews/", json={
        "product_id": test_product.id,
        "rating": 5,
        "comment": "Awesome"
    }, headers=headers_user)
    assert response.status_code == 201
    assert response.json()["rating"] == 5

@pytest.mark.asyncio
async def test_get_product_reviews(client: AsyncClient, test_product):
    response = await client.get(f"/reviews/product/{test_product.id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)