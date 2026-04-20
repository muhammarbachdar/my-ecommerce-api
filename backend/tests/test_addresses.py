import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_address(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/addresses/", json={
        "label": "Rumah",
        "recipient_name": "Test User",
        "phone": "08123456789",
        "full_address": "Jl. Merdeka No. 10",
        "city": "Jakarta",
        "province": "DKI Jakarta",
        "postal_code": "10110",
        "is_default": True
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["label"] == "Rumah"
    assert response.json()["is_default"] == True

@pytest.mark.asyncio
async def test_get_my_addresses(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Create one address first
    await client.post("/addresses/", json={
        "label": "Kantor",
        "recipient_name": "Test User",
        "phone": "08123456789",
        "full_address": "Jl. Sudirman",
        "city": "Jakarta",
        "province": "DKI Jakarta",
        "postal_code": "10220",
        "is_default": False
    }, headers=headers)
    response = await client.get("/addresses/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

@pytest.mark.asyncio
async def test_update_address(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    create_resp = await client.post("/addresses/", json={
        "label": "Update Test",
        "recipient_name": "Old Name",
        "phone": "08123456789",
        "full_address": "Jl. Lama",
        "city": "Jakarta",
        "province": "DKI",
        "postal_code": "10110",
        "is_default": False
    }, headers=headers)
    addr_id = create_resp.json()["id"]
    
    update_resp = await client.put(f"/addresses/{addr_id}", json={"recipient_name": "New Name", "is_default": True}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["recipient_name"] == "New Name"
    assert update_resp.json()["is_default"] == True