import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_workspace_creator_is_an_admin(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    me = (await client.get("/api/me", headers=headers)).json()
    assert me["role"] == "owner"
    assert me["is_admin"] is True


async def test_admin_can_switch_to_an_unlimited_plan(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    # The small demo-plan caps make limits cheap to hit in a test.
    await client.patch("/api/license", json={"plan": "demo"}, headers=headers)

    # The demo plan caps projects at 3.
    for i in range(3):
        assert (
            await client.post("/api/projects", json={"name": f"P{i}"}, headers=headers)
        ).status_code == 201
    blocked = await client.post("/api/projects", json={"name": "P4"}, headers=headers)
    assert blocked.status_code == 402

    upgraded = await client.patch("/api/license", json={"plan": "enterprise"}, headers=headers)
    assert upgraded.status_code == 200
    assert upgraded.json()["plan"] == "enterprise"
    assert upgraded.json()["project_limit"] == -1

    # Unlimited: what was blocked a moment ago now succeeds, repeatedly.
    for i in range(5):
        response = await client.post(
            "/api/projects", json={"name": f"Unlimited {i}"}, headers=headers
        )
        assert response.status_code == 201, response.text


async def test_usage_is_still_recorded_on_an_unlimited_plan(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    await client.patch("/api/license", json={"plan": "enterprise"}, headers=headers)
    await client.post("/api/projects", json={"name": "Tracked"}, headers=headers)

    usage = (await client.get("/api/usage", headers=headers)).json()
    assert usage["projects_used"] == 1
    assert usage["license"]["project_limit"] == -1


async def test_non_admin_cannot_change_the_plan_or_delete_projects(
    client: AsyncClient, registration_payload, db_session
):
    from sqlalchemy import select

    from app.models.membership import Membership, MembershipRole

    headers = await _register_and_get_headers(client, registration_payload)
    project_id = (
        await client.post("/api/projects", json={"name": "Kept"}, headers=headers)
    ).json()["id"]

    # Demote the workspace creator to a plain member.
    membership = await db_session.scalar(select(Membership))
    membership.role = MembershipRole.MEMBER
    await db_session.commit()

    me = (await client.get("/api/me", headers=headers)).json()
    assert me["is_admin"] is False

    assert (
        await client.patch("/api/license", json={"plan": "enterprise"}, headers=headers)
    ).status_code == 403
    assert (await client.delete(f"/api/projects/{project_id}", headers=headers)).status_code == 403


async def test_admin_can_delete_a_project_and_its_contracts(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = (
        await client.post("/api/projects", json={"name": "Retired tender"}, headers=headers)
    ).json()["id"]
    contract_id = (
        await client.post(
            f"/api/projects/{project_id}/contracts", json={"name": "MSA"}, headers=headers
        )
    ).json()["id"]

    response = await client.delete(f"/api/projects/{project_id}", headers=headers)
    assert response.status_code == 204

    assert (await client.get(f"/api/projects/{project_id}", headers=headers)).status_code == 404
    assert (await client.get("/api/projects", headers=headers)).json() == []
    # The contract went with it, in the org-wide list and by direct id.
    assert (await client.get("/api/contracts", headers=headers)).json() == []
    assert (await client.get(f"/api/contracts/{contract_id}", headers=headers)).status_code == 404


async def test_deleting_a_project_frees_its_plan_allowance(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    # The small demo-plan caps make limits cheap to hit in a test.
    await client.patch("/api/license", json={"plan": "demo"}, headers=headers)
    ids = []
    for i in range(3):
        ids.append(
            (await client.post("/api/projects", json={"name": f"P{i}"}, headers=headers)).json()["id"]
        )
    assert (await client.post("/api/projects", json={"name": "P4"}, headers=headers)).status_code == 402

    await client.delete(f"/api/projects/{ids[0]}", headers=headers)

    assert (
        await client.post("/api/projects", json={"name": "P4"}, headers=headers)
    ).status_code == 201


async def test_project_deletion_is_tenant_isolated(client: AsyncClient, registration_payload):
    owner_headers = await _register_and_get_headers(client, registration_payload)
    project_id = (
        await client.post("/api/projects", json={"name": "Owned"}, headers=owner_headers)
    ).json()["id"]

    outsider_headers = await _register_and_get_headers(
        client,
        {
            "email": "delete-outsider@example.com",
            "password": "SecurePass123",
            "full_name": "Outsider",
            "organization_name": "Outsider Org",
        },
    )
    response = await client.delete(f"/api/projects/{project_id}", headers=outsider_headers)
    assert response.status_code == 404
    assert (await client.get(f"/api/projects/{project_id}", headers=owner_headers)).status_code == 200
