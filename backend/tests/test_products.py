import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_product_unauthorized(client: AsyncClient):
    response = await client.post("/products/", json={
        "product_name": "Test Product",
        "price": 100,
        "stock": 10
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_product_as_admin(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.post("/products/", json={
        "product_name": "Admin Product",
        "price": 250000,
        "stock": 50,
        "description": "Nice item"
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["product_name"] == "Admin Product"
    assert data["price"] == 250000

@pytest.mark.asyncio
async def test_get_all_products(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.post("/products/", json={
        "product_name": "Laptop",
        "price": 5000000,
        "stock": 5
    }, headers=headers)
    response = await client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 1
    assert data["data"][0]["product_name"] == "Laptop"

@pytest.mark.asyncio
async def test_search_product(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.post("/products/", json={
        "product_name": "UniqueSearchMe",
        "price": 999,
        "stock": 2
    }, headers=headers)
    response = await client.get("/products/?q=UniqueSearchMe")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert any(p["product_name"] == "UniqueSearchMe" for p in data["data"])

@pytest.mark.asyncio
async def test_update_product_admin(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_resp = await client.post("/products/", json={
        "product_name": "ToUpdate",
        "price": 100,
        "stock": 1
    }, headers=headers)
    product_id = create_resp.json()["id"]
    
    update_resp = await client.put(f"/products/{product_id}", json={
        "product_name": "UpdatedName",
        "price": 200,
        "stock": 5,
        "description": "updated"
    }, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["product_name"] == "UpdatedName"

@pytest.mark.asyncio
async def test_delete_product_soft(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_resp = await client.post("/products/", json={
        "product_name": "ToDelete",
        "price": 50,
        "stock": 10
    }, headers=headers)
    product_id = create_resp.json()["id"]
    
    delete_resp = await client.delete(f"/products/{product_id}", headers=headers)
    assert delete_resp.status_code == 204
    
    get_resp = await client.get(f"/products/{product_id}")
    assert get_resp.status_code == 404