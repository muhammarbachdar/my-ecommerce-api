import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_checkout_creates_order(client: AsyncClient, user_token, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    prod = await client.post("/products/", json={
        "product_name": "Order Product",
        "price": 50000,
        "stock": 20
    }, headers=headers_admin)
    pid = prod.json()["id"]
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    await client.post("/carts/", json={"product_id": pid, "quantity": 2}, headers=headers_user)
    
    order_resp = await client.post("/orders/", json={"shipping_address": "Jl. Test No.1"}, headers=headers_user)
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert order_data["status"] == "pending"
    assert order_data["total_price"] == 50000 * 2

@pytest.mark.asyncio
async def test_get_my_orders(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.get("/orders/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data

@pytest.mark.asyncio
async def test_admin_update_order_status(client: AsyncClient, user_token, admin_token):
    # First create order as user
    headers_user = {"Authorization": f"Bearer {user_token}"}
    # Need a product in cart and checkout (simplify: reuse previous test or create new)
    # For brevity, assume we have at least one order from previous test
    # Get user orders to get order_id
    orders_resp = await client.get("/orders/me", headers=headers_user)
    orders = orders_resp.json()["data"]
    if not orders:
        # create one quickly
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        prod = await client.post("/products/", json={"product_name": "Status Test", "price": 1000, "stock": 10}, headers=headers_admin)
        pid = prod.json()["id"]
        await client.post("/carts/", json={"product_id": pid, "quantity": 1}, headers=headers_user)
        await client.post("/orders/", json={"shipping_address": "Addr"}, headers=headers_user)
        orders_resp = await client.get("/orders/me", headers=headers_user)
        orders = orders_resp.json()["data"]
    order_id = orders[0]["id"]
    
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    patch = await client.patch(f"/orders/{order_id}/status", params={"status": "paid"}, headers=headers_admin)
    assert patch.status_code == 200
    assert patch.json()["status"] == "paid"