import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_load_demo_project_creates_requirements_with_evidence(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)

    response = await client.post("/api/demo/load", headers=headers)
    assert response.status_code == 201
    project = response.json()
    assert project["is_demo"] is True
    assert project["analysis_status"] == "completed"

    requirements_response = await client.get(
        f"/api/projects/{project['id']}/requirements", headers=headers
    )
    requirements = requirements_response.json()
    from app.services.demo_fixtures import DEMO_REQUIREMENTS

    assert len(requirements) == len(DEMO_REQUIREMENTS)

    statuses = {r["assessment"]["status"] for r in requirements}
    # The demo data must cover more than a single monotone status — this is
    # what section 14/28 of the brief calls a "convincing" demo, not just a
    # sea of green.
    assert "evidence_not_found" in statuses
    assert "compliant_looking" in statuses or "human_verified" in statuses
    assert "partially_addressed" in statuses
    assert "potential_non_compliance" in statuses

    # The missing mandatory form is the demo's headline finding: reported as
    # not located, with no evidence records invented to fill the gap.
    missing_form_c = next(r for r in requirements if r["source_clause"] == "8.3")
    detail = (
        await client.get(f"/api/requirements/{missing_form_c['id']}", headers=headers)
    ).json()
    assert detail["assessment"]["status"] == "evidence_not_found"
    assert detail["assessment"]["priority"] == "critical"


async def test_loading_the_demo_twice_does_not_duplicate_it(
    client: AsyncClient, registration_payload
):
    """Regression test: each click of "Try the sample project" used to seed a
    fresh copy, so a user who clicked twice ended up with identical duplicate
    projects cluttering their list."""
    headers = await _register_and_get_headers(client, registration_payload)

    first = await client.post("/api/demo/load", headers=headers)
    second = await client.post("/api/demo/load", headers=headers)

    assert first.json()["id"] == second.json()["id"]

    projects = (await client.get("/api/projects", headers=headers)).json()
    assert len([p for p in projects if p["is_demo"]]) == 1


async def test_each_module_seeds_its_own_sample_independently(
    client: AsyncClient, registration_payload
):
    """Regression test: both modules mark their sample project is_demo, so an
    "already loaded?" check on that flag alone made whichever sample loaded
    second silently return the other module's project."""
    headers = await _register_and_get_headers(client, registration_payload)

    contract = (await client.post("/api/clauserisk/demo/load", headers=headers)).json()
    project = (await client.post("/api/demo/load", headers=headers)).json()

    assert project["id"] != contract["project_id"]
    assert project["analysis_status"] == "completed"

    projects = (await client.get("/api/projects", headers=headers)).json()
    demo_names = sorted(p["name"] for p in projects if p["is_demo"])
    assert len(demo_names) == 2


async def test_demo_project_carries_a_live_submission_deadline(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    project = (await client.post("/api/demo/load", headers=headers)).json()
    assert project["submission_deadline"] is not None


async def test_demo_documents_have_real_extracted_text(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.post("/api/demo/load", headers=headers)
    project_id = response.json()["id"]

    documents_response = await client.get(f"/api/projects/{project_id}/documents", headers=headers)
    documents = documents_response.json()
    assert len(documents) == 2
    assert {d["document_type"] for d in documents} == {"tender", "bid"}
    for doc in documents:
        assert doc["extraction_status"] == "completed"
        assert doc["page_count"] and doc["page_count"] > 0
