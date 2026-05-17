import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_add_to_wishlist(client: AsyncClient, user_token, test_product):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/wishlist/", json={"product_id": test_product.id}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == test_product.id
    assert data["product_name"] == test_product.product_name

@pytest.mark.asyncio
async def test_get_wishlist(client: AsyncClient, user_token, test_product):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Add first
    await client.post("/wishlist/", json={"product_id": test_product.id}, headers=headers)
    response = await client.get("/wishlist/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # Response sekarang paginated: { "data": [...], "pagination": {...} }
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["product_id"] == test_product.id

@pytest.mark.asyncio
async def test_remove_from_wishlist(client: AsyncClient, user_token, test_product):
    headers = {"Authorization": f"Bearer {user_token}"}
    await client.post("/wishlist/", json={"product_id": test_product.id}, headers=headers)
    delete_response = await client.delete(f"/wishlist/{test_product.id}", headers=headers)
    assert delete_response.status_code == 204
    # Verify removal
    get_response = await client.get("/wishlist/", headers=headers)
    assert get_response.status_code == 200
    data = get_response.json()
    assert len(data["data"]) == 0