import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_creates_account_and_returns_tokens(
    client: AsyncClient, registration_payload
):
    response = await client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_register_rejects_duplicate_email(client: AsyncClient, registration_payload):
    await client.post("/api/auth/register", json=registration_payload)
    response = await client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 409


async def test_login_with_correct_credentials(client: AsyncClient, registration_payload):
    await client.post("/api/auth/register", json=registration_payload)
    response = await client.post(
        "/api/auth/login",
        json={
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_with_wrong_password_is_rejected(client: AsyncClient, registration_payload):
    await client.post("/api/auth/register", json=registration_payload)
    response = await client.post(
        "/api/auth/login",
        json={"email": registration_payload["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get("/api/me")
    assert response.status_code == 401


async def test_me_returns_user_and_organization(client: AsyncClient, registration_payload):
    register_response = await client.post("/api/auth/register", json=registration_payload)
    token = register_response.json()["access_token"]

    response = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == registration_payload["email"]
    assert body["organization"]["name"] == registration_payload["organization_name"]


async def test_refresh_issues_new_access_token(client: AsyncClient, registration_payload):
    register_response = await client.post("/api/auth/register", json=registration_payload)
    refresh_token = register_response.json()["refresh_token"]

    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_access_token_rejected_by_refresh_endpoint(
    client: AsyncClient, registration_payload
):
    register_response = await client.post("/api/auth/register", json=registration_payload)
    access_token = register_response.json()["access_token"]

    response = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401
