import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_categories_public(client: AsyncClient, test_category):
    response = await client.get("/categories/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 1

@pytest.mark.asyncio
async def test_create_category_admin(client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.post("/categories/categories", json={
        "name": "Clothing",
        "slug": "clothing"
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Clothing"

@pytest.mark.asyncio
async def test_create_category_unauthorized(client: AsyncClient):
    response = await client.post("/categories/categories", json={
        "name": "Illegal",
        "slug": "illegal"
    })
    # FastAPI returns 403 for missing role, not 401
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_category_admin(client: AsyncClient, admin_token, test_category):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.put(f"/categories/categories/{test_category.id}", json={
        "name": "Updated Electronics",
        "slug": "updated-elec"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Electronics"

@pytest.mark.asyncio
async def test_delete_category_admin(client: AsyncClient, admin_token, test_category):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.delete(f"/categories/categories/{test_category.id}", headers=headers)
    assert response.status_code == 204