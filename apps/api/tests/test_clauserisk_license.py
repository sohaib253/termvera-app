import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_demo_plan_includes_both_modules_by_default(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.get("/api/license", headers=headers)
    body = response.json()
    assert set(body["enabled_modules"]) == {"tenderguard", "clauserisk"}


async def test_contract_creation_succeeds_when_module_entitled(
    client: AsyncClient, registration_payload
):
    """The demo plan enables ClauseRisk by default (see the test above),
    so contract creation should pass the module gate. The gate's reject
    path is exercised directly in test_module_gate_rejects_when_disabled
    below — there's no license-admin endpoint yet to disable a module
    through the API (see docs/licensing.md)."""
    headers = await _register_and_get_headers(client, registration_payload)
    project_response = await client.post("/api/projects", json={"name": "P"}, headers=headers)
    project_id = project_response.json()["id"]

    response = await client.post(
        f"/api/projects/{project_id}/contracts",
        json={"name": "Sample Contract"},
        headers=headers,
    )
    assert response.status_code == 201


async def test_contract_limit_is_enforced(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_response = await client.post("/api/projects", json={"name": "P"}, headers=headers)
    project_id = project_response.json()["id"]

    for i in range(10):
        response = await client.post(
            f"/api/projects/{project_id}/contracts",
            json={"name": f"Contract {i}"},
            headers=headers,
        )
        assert response.status_code == 201, response.text

    over_limit_response = await client.post(
        f"/api/projects/{project_id}/contracts",
        json={"name": "One too many"},
        headers=headers,
    )
    assert over_limit_response.status_code == 402


async def test_module_gate_rejects_when_disabled(db_session):
    """Unit-level test of the gate itself (not reachable end-to-end without
    a license-admin endpoint, which doesn't exist yet — see
    docs/licensing.md): directly disable ClauseRisk on a license row and
    confirm check_module_entitlement raises."""
    from app.models.license import LicenseAccount, LicenseModule
    from app.services import license as license_service

    account = LicenseAccount(organization_id="org-under-test", enabled_modules="[\"tenderguard\"]")
    db_session.add(account)
    await db_session.commit()

    with pytest.raises(license_service.ModuleNotEntitledError):
        await license_service.check_module_entitlement(
            db_session, organization_id="org-under-test", module=LicenseModule.CLAUSERISK
        )
