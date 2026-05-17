import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_add_to_cart(client: AsyncClient, user_token, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    product_resp = await client.post("/products/", json={
        "product_name": "Cart Item",
        "price": 75000,
        "stock": 100
    }, headers=headers_admin)
    product_id = product_resp.json()["id"]
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/carts/", json={
        "product_id": product_id,
        "quantity": 2
    }, headers=headers_user)
    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == product_id
    assert data["quantity"] == 2

@pytest.mark.asyncio
async def test_get_cart(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.get("/carts/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data

@pytest.mark.asyncio
async def test_update_cart_item(client: AsyncClient, user_token, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    prod = await client.post("/products/", json={
        "product_name": "Update Cart",
        "price": 100,
        "stock": 50
    }, headers=headers_admin)
    pid = prod.json()["id"]
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    add = await client.post("/carts/", json={"product_id": pid, "quantity": 1}, headers=headers_user)
    item_id = add.json()["id"]
    
    update = await client.put(f"/carts/{item_id}", json={"quantity": 5}, headers=headers_user)
    assert update.status_code == 200
    assert update.json()["quantity"] == 5

@pytest.mark.asyncio
async def test_remove_from_cart(client: AsyncClient, user_token, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    prod = await client.post("/products/", json={
        "product_name": "Remove Cart",
        "price": 200,
        "stock": 30
    }, headers=headers_admin)
    pid = prod.json()["id"]
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    add = await client.post("/carts/", json={"product_id": pid, "quantity": 1}, headers=headers_user)
    item_id = add.json()["id"]
    
    delete = await client.delete(f"/carts/{item_id}", headers=headers_user)
    assert delete.status_code == 204