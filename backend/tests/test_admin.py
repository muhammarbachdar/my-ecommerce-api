import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_dashboard_access_denied_for_user(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 403
    assert "Admin access required" in response.text

@pytest.mark.asyncio
async def test_admin_dashboard_success(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_orders" in data
    assert "total_revenue" in data
    assert "orders_by_status" in data
    assert "top_products" in data