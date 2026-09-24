import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_default_license_is_demo_plan(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.get("/api/license", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "demo"
    assert body["status"] == "active"
    assert body["project_limit"] == 3


async def test_project_limit_is_enforced(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)

    for i in range(3):
        response = await client.post(
            "/api/projects", json={"name": f"Project {i}"}, headers=headers
        )
        assert response.status_code == 201

    over_limit_response = await client.post(
        "/api/projects", json={"name": "One too many"}, headers=headers
    )
    assert over_limit_response.status_code == 402


async def test_usage_endpoint_reflects_project_count(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    await client.post("/api/projects", json={"name": "Tracked Project"}, headers=headers)

    response = await client.get("/api/usage", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["projects_used"] == 1
    assert body["license"]["plan"] == "demo"
