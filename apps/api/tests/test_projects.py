import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_project_requires_auth(client: AsyncClient):
    response = await client.post("/api/projects", json={"name": "Offshore Package"})
    assert response.status_code == 401


async def test_create_and_list_project(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)

    create_response = await client.post(
        "/api/projects",
        json={
            "name": "North Field Offshore Well Testing Package",
            "client_name": "Example Energy Company",
            "tender_reference": "ITB-2026-001",
            "sector": "Oil & Gas",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "draft"
    assert created["name"] == "North Field Offshore Well Testing Package"

    list_response = await client.get("/api/projects", headers=headers)
    assert list_response.status_code == 200
    projects = list_response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == created["id"]


async def test_create_project_rejects_blank_name(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.post("/api/projects", json={"name": ""}, headers=headers)
    assert response.status_code == 422


async def test_get_missing_project_returns_404(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.get("/api/projects/does-not-exist", headers=headers)
    assert response.status_code == 404


async def test_patch_updates_project_status(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    create_response = await client.post(
        "/api/projects", json={"name": "Test Project"}, headers=headers
    )
    project_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/projects/{project_id}", json={"status": "active"}, headers=headers
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "active"
