import io

import fitz
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _make_pdf_bytes(text: str = "Hello requirement text for testing.") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, headers) -> str:
    response = await client.post("/api/projects", json={"name": "Doc Test Project"}, headers=headers)
    return response.json()["id"]


def _make_docx_bytes() -> bytes:
    import docx
    from docx.enum.text import WD_BREAK

    document = docx.Document()
    document.add_paragraph("The Bidder shall provide evidence of prior experience.")
    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    document.add_paragraph("Schedule of rates")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Day rate"
    table.rows[0].cells[1].text = "USD 1,200"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


async def test_upload_rejects_unsupported_format(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)

    response = await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "tender"},
        files={"file": ("setup.exe", b"MZ not a document", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert "not supported" in response.json()["error"]["message"]


async def test_upload_rejects_file_that_only_claims_to_be_pdf(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)

    response = await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "tender"},
        files={"file": ("tender.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 422


async def test_upload_and_extract_word_document(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)

    response = await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "tender"},
        files={
            "file": (
                "tender.docx",
                _make_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    detail = await client.get(f"/api/projects/{project_id}/documents/{document_id}", headers=headers)
    assert detail.json()["extraction_status"] == "completed"
    assert detail.json()["page_count"] == 2  # split at the explicit page break

    pages = (
        await client.get(f"/api/projects/{project_id}/documents/{document_id}/pages", headers=headers)
    ).json()
    assert "prior experience" in pages[0]["text"]
    assert "Day rate | USD 1,200" in pages[1]["text"]  # table rows are kept


async def test_upload_and_extract_text_file(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)

    response = await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "reference"},
        files={"file": ("notes.txt", b"The Bidder shall hold ISO 9001.", "text/plain")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    pages = (
        await client.get(f"/api/projects/{project_id}/documents/{document_id}/pages", headers=headers)
    ).json()
    assert pages[0]["text"] == "The Bidder shall hold ISO 9001."


async def test_upload_and_extract_pdf(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)

    pdf_bytes = _make_pdf_bytes("The Bidder shall provide evidence of prior experience.")
    response = await client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        data={"document_type": "tender"},
        files={"file": ("tender.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["extraction_status"] == "pending"

    # BackgroundTasks run synchronously within the ASGI test transport's
    # request/response cycle in this app configuration, so poll briefly.
    document_id = document["id"]

    status_response = await client.get(
        f"/api/projects/{project_id}/documents/{document_id}", headers=headers
    )
    assert status_response.json()["extraction_status"] == "completed"
    assert status_response.json()["page_count"] == 1

    pages_response = await client.get(
        f"/api/projects/{project_id}/documents/{document_id}/pages", headers=headers
    )
    assert pages_response.status_code == 200
    pages = pages_response.json()
    assert len(pages) == 1
    assert "prior experience" in pages[0]["text"]

    file_response = await client.get(
        f"/api/projects/{project_id}/documents/{document_id}/file", headers=headers
    )
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/pdf"


async def test_document_tenant_isolation(client: AsyncClient):
    org_a_headers = await _register_and_get_headers(
        client,
        {
            "email": "docowner@example.com",
            "password": "SecurePass123",
            "full_name": "Doc Owner",
            "organization_name": "Doc Org A",
        },
    )
    org_b_headers = await _register_and_get_headers(
        client,
        {
            "email": "docoutsider@example.com",
            "password": "SecurePass123",
            "full_name": "Doc Outsider",
            "organization_name": "Doc Org B",
        },
    )
    project_id = await _create_project(client, org_a_headers)

    response = await client.get(f"/api/projects/{project_id}/documents", headers=org_b_headers)
    assert response.status_code == 404
