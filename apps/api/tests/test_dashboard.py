import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_summary_is_empty_for_a_new_organization(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)

    response = await client.get("/api/dashboard/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["projects_total"] == 0
    assert body["contracts_total"] == 0
    assert body["upcoming_deadlines"] == []
    assert body["findings_by_severity"]["critical"] == 0


async def test_summary_counts_projects_deadlines_and_review_queue(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)

    await client.post(
        "/api/projects",
        json={"name": "Closing soon", "submission_deadline": "2099-01-15"},
        headers=headers,
    )
    await client.post("/api/projects", json={"name": "No deadline"}, headers=headers)
    # The demo project seeds requirements that need human review, which is
    # what makes the "awaiting review" count meaningful.
    await client.post("/api/demo/load", headers=headers)

    response = await client.get("/api/dashboard/summary", headers=headers)
    body = response.json()

    assert body["projects_total"] == 3

    deadlines = body["upcoming_deadlines"]
    names = [d["name"] for d in deadlines]
    assert "Closing soon" in names
    assert "No deadline" not in names
    # Soonest first: the sample project closes in ~12 days, well before 2099.
    assert deadlines == sorted(deadlines, key=lambda d: d["days_remaining"])
    assert all(d["days_remaining"] > 0 for d in deadlines)

    assert body["requirements_awaiting_review"] > 0
    assert body["critical_requirements"] > 0


async def test_summary_is_tenant_isolated(client: AsyncClient, registration_payload):
    owner_headers = await _register_and_get_headers(client, registration_payload)
    await client.post("/api/projects", json={"name": "Owner project"}, headers=owner_headers)

    outsider_headers = await _register_and_get_headers(
        client,
        {
            "email": "dashboard-outsider@example.com",
            "password": "SecurePass123",
            "full_name": "Outsider",
            "organization_name": "Outsider Org",
        },
    )
    response = await client.get("/api/dashboard/summary", headers=outsider_headers)
    assert response.json()["projects_total"] == 0


async def test_summary_counts_contract_findings_by_severity(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    import io

    import fitz

    def _pdf(text: str) -> bytes:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=10)
        buffer = io.BytesIO()
        doc.save(buffer)
        doc.close()
        return buffer.getvalue()

    headers = await _register_and_get_headers(client, registration_payload)
    project_id = (
        await client.post("/api/projects", json={"name": "Contract project"}, headers=headers)
    ).json()["id"]
    contract_id = (
        await client.post(
            f"/api/projects/{project_id}/contracts",
            json={"name": "MSA"},
            headers=headers,
        )
    ).json()["id"]
    version = await client.post(
        f"/api/contracts/{contract_id}/versions",
        headers=headers,
        data={"version_label": "v1"},
        files={
            "file": (
                "c.pdf",
                _pdf("12.3 Limitation of Liability\nLiability shall not exceed 20%.\n"),
                "application/pdf",
            )
        },
    )
    await client.post(
        f"/api/contract-versions/{version.json()['id']}/analysis", headers=headers
    )

    body = (await client.get("/api/dashboard/summary", headers=headers)).json()
    assert body["contracts_total"] == 1
    assert body["contracts_analyzed"] == 1
    assert sum(body["findings_by_severity"].values()) > 0
    assert body["findings_unreviewed"] > 0
