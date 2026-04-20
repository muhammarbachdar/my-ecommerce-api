import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_payment_mock(client: AsyncClient, user_token, test_order):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/payments/", json={
        "order_id": test_order.id,
        "method": "bank_transfer"
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["order_id"] == test_order.id
    assert data["status"] == "pending"
    assert "payment_url" in data

@pytest.mark.asyncio
async def test_get_payment_by_order(client: AsyncClient, user_token, test_order):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Create payment first
    await client.post("/payments/", json={"order_id": test_order.id, "method": "ewallet"}, headers=headers)
    response = await client.get(f"/payments/order/{test_order.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["order_id"] == test_order.id

@pytest.mark.asyncio
async def test_admin_confirm_payment(client: AsyncClient, admin_token, test_order):
    # Create payment as user
    user_token = (await client.post("/auth/login", json={"email": "test@example.com", "password": "12345678"})).json()["access_token"]
    payment_resp = await client.post("/payments/", json={"order_id": test_order.id, "method": "transfer"}, headers={"Authorization": f"Bearer {user_token}"})
    payment_id = payment_resp.json()["id"]
    
    # Confirm as admin
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    confirm = await client.patch(f"/payments/{payment_id}/confirm", headers=headers_admin)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "paid"
    assert confirm.json()["paid_at"] is not None