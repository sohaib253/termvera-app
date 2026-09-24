import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _load_demo_and_get_requirement(client: AsyncClient, headers, clause: str) -> dict:
    demo_response = await client.post("/api/demo/load", headers=headers)
    project_id = demo_response.json()["id"]
    requirements_response = await client.get(
        f"/api/projects/{project_id}/requirements", headers=headers
    )
    return next(r for r in requirements_response.json() if r["source_clause"] == clause)


async def test_review_action_appears_immediately_in_response(
    client: AsyncClient, registration_payload
):
    """Regression test: applying a review action must return the updated
    review_actions list in the SAME response — a prior bug re-queried the
    requirement using a session that still had the pre-review collection
    cached in its identity map, so the freshly-added review action was
    silently missing from the response even though it was correctly
    persisted to the database."""
    headers = await _register_and_get_headers(client, registration_payload)
    requirement = await _load_demo_and_get_requirement(client, headers, "8.3")

    assert requirement["assessment"]["status"] == "evidence_not_found"

    response = await client.post(
        f"/api/requirements/{requirement['id']}/review",
        json={"new_status": "human_rejected", "comment": "Confirmed genuinely missing."},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["assessment"]["status"] == "human_rejected"
    assert body["assessment"]["reviewer_status"] == "reviewed"
    assert body["assessment"]["requires_human_review"] is False
    assert len(body["review_actions"]) == 1
    action = body["review_actions"][0]
    assert action["previous_status"] == "evidence_not_found"
    assert action["new_status"] == "human_rejected"
    assert action["comment"] == "Confirmed genuinely missing."

    # And it must still be there on a fresh GET, not just the mutation response.
    detail_response = await client.get(f"/api/requirements/{requirement['id']}", headers=headers)
    assert len(detail_response.json()["review_actions"]) == 1


async def test_comment_only_review_action_does_not_change_status(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    requirement = await _load_demo_and_get_requirement(client, headers, "3.1")
    original_status = requirement["assessment"]["status"]

    response = await client.post(
        f"/api/requirements/{requirement['id']}/review",
        json={"comment": "Just leaving a note, no status change."},
        headers=headers,
    )
    body = response.json()
    assert body["assessment"]["status"] == original_status
    assert len(body["review_actions"]) == 1
    assert body["review_actions"][0]["action_type"] == "comment"
    assert body["review_actions"][0]["new_status"] is None


async def test_multiple_review_actions_accumulate(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    requirement = await _load_demo_and_get_requirement(client, headers, "3.3")

    await client.post(
        f"/api/requirements/{requirement['id']}/review",
        json={"comment": "First note."},
        headers=headers,
    )
    second_response = await client.post(
        f"/api/requirements/{requirement['id']}/review",
        json={"new_status": "potential_non_compliance", "comment": "Second note."},
        headers=headers,
    )
    assert len(second_response.json()["review_actions"]) == 2


async def test_requirement_detail_tenant_isolation(client: AsyncClient):
    org_a_headers = await _register_and_get_headers(
        client,
        {
            "email": "reqowner@example.com",
            "password": "SecurePass123",
            "full_name": "Req Owner",
            "organization_name": "Req Org A",
        },
    )
    org_b_headers = await _register_and_get_headers(
        client,
        {
            "email": "reqoutsider@example.com",
            "password": "SecurePass123",
            "full_name": "Req Outsider",
            "organization_name": "Req Org B",
        },
    )
    requirement = await _load_demo_and_get_requirement(client, org_a_headers, "8.3")

    get_response = await client.get(f"/api/requirements/{requirement['id']}", headers=org_b_headers)
    assert get_response.status_code == 404

    review_response = await client.post(
        f"/api/requirements/{requirement['id']}/review",
        json={"comment": "should not work"},
        headers=org_b_headers,
    )
    assert review_response.status_code == 404
