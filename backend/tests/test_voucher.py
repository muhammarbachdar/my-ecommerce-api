import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone

@pytest.mark.asyncio
async def test_admin_create_voucher(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    now = datetime.now(timezone.utc)
    response = await client.post("/vouchers/admin", json={
        "code": "TEST10",
        "name": "Test Discount",
        "discount_type": "percentage",
        "discount_value": 10,
        "min_purchase": 50000,
        "max_discount": 20000,
        "usage_limit": 100,
        "usage_per_user": 1,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat()
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["code"] == "TEST10"

@pytest.mark.asyncio
async def test_user_get_available_vouchers(client: AsyncClient, user_token, admin_token):
    # Create voucher first
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    now = datetime.now(timezone.utc)
    await client.post("/vouchers/admin", json={
        "code": "AVAIL",
        "name": "Available",
        "discount_type": "fixed",
        "discount_value": 10000,
        "min_purchase": 0,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=1)).isoformat()
    }, headers=headers_admin)
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    response = await client.get("/vouchers/available", headers=headers_user)
    assert response.status_code == 200
    assert len(response.json()) >= 1

@pytest.mark.asyncio
async def test_user_claim_voucher(client: AsyncClient, user_token, admin_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    now = datetime.now(timezone.utc)
    voucher_resp = await client.post("/vouchers/admin", json={
        "code": "CLAIMIT",
        "name": "Claimable",
        "discount_type": "percentage",
        "discount_value": 15,
        "min_purchase": 0,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=1)).isoformat()
    }, headers=headers_admin)
    voucher_id = voucher_resp.json()["id"]
    
    headers_user = {"Authorization": f"Bearer {user_token}"}
    claim = await client.post(f"/vouchers/{voucher_id}/claim", headers=headers_user)
    assert claim.status_code == 200
    assert claim.json()["voucher_id"] == voucher_id