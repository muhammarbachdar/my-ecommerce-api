import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": "newuser@example.com",
        "password": "12345678"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "12345678"
    })
    assert response.status_code == 400
    assert "Email already registered" in response.text

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "12345678"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    response = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    login_resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "12345678"
    })
    refresh_token = login_resp.json()["refresh_token"]
    response = await client.post("/auth/refresh", params={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_logout(client: AsyncClient, user_token, user_refresh_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.post("/auth/logout", params={"refresh_token": user_refresh_token}, headers=headers)
    assert response.status_code == 204