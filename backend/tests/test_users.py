import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.put("/users/me", json={"name": "Updated Name", "phone": "0811111111"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["phone"] == "0811111111"

@pytest.mark.asyncio
async def test_admin_get_all_users(client: AsyncClient, admin_token, test_user):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/users/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Sekarang ada test_user (dari fixture) dan admin (dari login)
    assert len(data["data"]) >= 2
@pytest.mark.asyncio
async def test_admin_ban_user(client: AsyncClient, admin_token, test_user):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.patch(f"/users/{test_user.id}/ban", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_deleted"] == True