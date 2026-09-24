import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_organization_cannot_see_another_organizations_projects(client: AsyncClient):
    org_a_headers = await _register_and_get_headers(
        client,
        {
            "email": "usera@example.com",
            "password": "SecurePass123",
            "full_name": "User A",
            "organization_name": "Contractor A",
        },
    )
    org_b_headers = await _register_and_get_headers(
        client,
        {
            "email": "userb@example.com",
            "password": "SecurePass123",
            "full_name": "User B",
            "organization_name": "Contractor B",
        },
    )

    create_response = await client.post(
        "/api/projects", json={"name": "Contractor A Confidential Bid"}, headers=org_a_headers
    )
    project_id = create_response.json()["id"]

    # Org B must not be able to read Org A's project by id.
    get_response = await client.get(f"/api/projects/{project_id}", headers=org_b_headers)
    assert get_response.status_code == 404

    # Org B must not be able to modify it either.
    patch_response = await client.patch(
        f"/api/projects/{project_id}", json={"status": "active"}, headers=org_b_headers
    )
    assert patch_response.status_code == 404

    # Org B's project list must not include Org A's project.
    list_response = await client.get("/api/projects", headers=org_b_headers)
    assert list_response.status_code == 200
    assert all(p["id"] != project_id for p in list_response.json())
