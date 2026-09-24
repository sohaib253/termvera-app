import io

import fitz
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=10)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


V1_TEXT = (
    "5.1 Payment Terms\n"
    "The Client shall pay within 45 days of a valid invoice.\n"
    "8.1 Liquidated Damages\n"
    "Liquidated damages of USD 5,000 per day shall apply, capped at 10%.\n"
    "9.1 Confidentiality\n"
    "Both parties shall keep contract terms confidential.\n"
)

V2_TEXT = (
    "5.1 Payment Terms\n"
    "The Client shall pay within 30 days of a valid invoice.\n"
    "8.1 Liquidated Damages\n"
    "Liquidated damages of USD 5,000 per day shall apply, capped at 10%.\n"
    "10.1 Governing Law\n"
    "This Agreement is governed by the laws of England and Wales.\n"
)


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _setup_contract_with_two_versions(client: AsyncClient, headers) -> tuple[str, str, str]:
    project_response = await client.post(
        "/api/projects", json={"name": "Comparison Project"}, headers=headers
    )
    project_id = project_response.json()["id"]

    contract_response = await client.post(
        f"/api/projects/{project_id}/contracts",
        json={"name": "Master Services Agreement"},
        headers=headers,
    )
    contract_id = contract_response.json()["id"]

    v1_response = await client.post(
        f"/api/contracts/{contract_id}/versions",
        headers=headers,
        data={"version_label": "Original"},
        files={"file": ("v1.pdf", _make_pdf_bytes(V1_TEXT), "application/pdf")},
    )
    v2_response = await client.post(
        f"/api/contracts/{contract_id}/versions",
        headers=headers,
        data={"version_label": "Amendment 1"},
        files={"file": ("v2.pdf", _make_pdf_bytes(V2_TEXT), "application/pdf")},
    )
    return contract_id, v1_response.json()["id"], v2_response.json()["id"]


async def test_comparison_detects_added_deleted_and_modified_clauses(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    headers = await _register_and_get_headers(client, registration_payload)
    contract_id, v1_id, v2_id = await _setup_contract_with_two_versions(client, headers)

    # Run analysis on both versions so clauses/amounts/dates are populated
    # for the diff to work against (comparison reads Clause rows, which
    # only exist after the pipeline has run).
    await client.post(f"/api/contract-versions/{v1_id}/analysis", headers=headers)
    await client.post(f"/api/contract-versions/{v2_id}/analysis", headers=headers)

    response = await client.post(
        f"/api/contracts/{contract_id}/comparisons",
        json={"base_version_id": v1_id, "compared_version_id": v2_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    changes = {c["clause_number"]: c for c in body["changes"]}

    assert changes["9.1"]["change_type"] == "deleted"
    assert changes["10.1"]["change_type"] == "added"
    assert changes["5.1"]["change_type"] == "modified"
    description_5_1 = changes["5.1"]["description"]
    assert "45" in description_5_1 or "30" in description_5_1 or "changed" in description_5_1
    # 8.1's liquidated damages figures are identical between versions —
    # should NOT show up as a change at all.
    assert "8.1" not in changes


async def test_comparison_requires_both_versions_belong_to_contract(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    headers = await _register_and_get_headers(client, registration_payload)
    contract_id, v1_id, _v2_id = await _setup_contract_with_two_versions(client, headers)

    other_project = await client.post("/api/projects", json={"name": "Other"}, headers=headers)
    other_contract = await client.post(
        f"/api/projects/{other_project.json()['id']}/contracts",
        json={"name": "Unrelated Contract"},
        headers=headers,
    )
    other_version = await client.post(
        f"/api/contracts/{other_contract.json()['id']}/versions",
        headers=headers,
        data={"version_label": "v1"},
        files={"file": ("other.pdf", _make_pdf_bytes("1.1 Some clause.\nText."), "application/pdf")},
    )

    response = await client.post(
        f"/api/contracts/{contract_id}/comparisons",
        json={"base_version_id": v1_id, "compared_version_id": other_version.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 404
