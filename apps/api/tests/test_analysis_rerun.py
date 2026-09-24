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


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_rerunning_analysis_does_not_duplicate_requirements(
    client: AsyncClient, registration_payload, tenderguard_fake_provider
):
    """Regression test: running analysis twice on the same project used to
    duplicate every Requirement (the pipeline only ever appended new rows).
    Discovered via a real Ollama-backed ClauseRisk run that got re-triggered
    after a server restart — the identical bug exists here since both
    pipelines share the same "regenerate on run" shape."""
    headers = await _register_and_get_headers(client, registration_payload)
    project_response = await client.post(
        "/api/projects", json={"name": "Rerun Test Project"}, headers=headers
    )
    project_id = project_response.json()["id"]

    tender_pdf = _make_pdf_bytes("The Bidder shall submit a valid license.")
    await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "tender"},
        files={"file": ("tender.pdf", tender_pdf, "application/pdf")},
    )
    await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "bid"},
        files={"file": ("bid.pdf", _make_pdf_bytes("Our company holds a valid license."), "application/pdf")},
    )

    first_run = await client.post(f"/api/projects/{project_id}/analysis", headers=headers)
    assert first_run.status_code == 202

    status_response = await client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert status_response.json()["analysis_status"] == "completed"

    requirements_after_first_run = (
        await client.get(f"/api/projects/{project_id}/requirements", headers=headers)
    ).json()
    assert len(requirements_after_first_run) == 1

    second_run = await client.post(f"/api/projects/{project_id}/analysis", headers=headers)
    assert second_run.status_code == 202

    requirements_after_second_run = (
        await client.get(f"/api/projects/{project_id}/requirements", headers=headers)
    ).json()
    assert len(requirements_after_second_run) == 1
    assert tenderguard_fake_provider.extract_calls == 2
