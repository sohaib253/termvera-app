import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_new_workspace_starts_a_full_featured_trial(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.get("/api/license", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "trial"
    assert body["state"] == "trial"
    assert body["days_left"] == 14
    assert body["read_only"] is False
    assert sorted(body["enabled_modules"]) == ["clauserisk", "tenderguard"]


async def test_project_limit_is_enforced(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    # The small demo-plan caps make limits cheap to hit in a test.
    await client.patch("/api/license", json={"plan": "demo"}, headers=headers)

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
    assert body["license"]["plan"] == "trial"
