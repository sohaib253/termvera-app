import io

import fitz
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _make_pdf_bytes(clauses_text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), clauses_text, fontsize=10)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


SAMPLE_CONTRACT_TEXT = (
    "12.3 Limitation of Liability\n"
    "The Contractor's aggregate liability shall not exceed 20% of the Contract Price.\n"
    "12.4 Indemnity\n"
    "The Contractor shall indemnify the Client against third-party claims, without limit.\n"
)


async def _register_and_get_headers(client: AsyncClient, payload) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, headers) -> str:
    response = await client.post("/api/projects", json={"name": "Contract Review Project"}, headers=headers)
    return response.json()["id"]


async def _create_contract(client: AsyncClient, headers, project_id: str) -> str:
    response = await client.post(
        f"/api/projects/{project_id}/contracts",
        json={"name": "Services Agreement", "contract_type": "services", "counterparty_name": "Acme Corp"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _upload_version(
    client: AsyncClient, headers, contract_id: str, text: str = SAMPLE_CONTRACT_TEXT
) -> dict:
    pdf_bytes = _make_pdf_bytes(text)
    response = await client.post(
        f"/api/contracts/{contract_id}/versions",
        headers=headers,
        data={"version_label": "v1"},
        files={"file": ("contract.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_contract_and_upload_version(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)

    version = await _upload_version(client, headers, contract_id)
    assert version["version_number"] == 1
    assert version["analysis_status"] == "not_started"

    detail_response = await client.get(f"/api/contracts/{contract_id}", headers=headers)
    detail = detail_response.json()
    assert len(detail["versions"]) == 1


async def test_contract_tenant_isolation(client: AsyncClient):
    org_a_headers = await _register_and_get_headers(
        client,
        {
            "email": "contractowner@example.com",
            "password": "SecurePass123",
            "full_name": "Contract Owner",
            "organization_name": "Contract Org A",
        },
    )
    org_b_headers = await _register_and_get_headers(
        client,
        {
            "email": "contractoutsider@example.com",
            "password": "SecurePass123",
            "full_name": "Contract Outsider",
            "organization_name": "Contract Org B",
        },
    )
    project_id = await _create_project(client, org_a_headers)
    contract_id = await _create_contract(client, org_a_headers, project_id)

    response = await client.get(f"/api/contracts/{contract_id}", headers=org_b_headers)
    assert response.status_code == 404


async def test_full_pipeline_runs_and_produces_scored_findings(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version = await _upload_version(client, headers, contract_id)
    version_id = version["id"]

    analysis_response = await client.post(
        f"/api/contract-versions/{version_id}/analysis", headers=headers
    )
    assert analysis_response.status_code == 200, analysis_response.text
    assert analysis_response.json()["analysis_status"] == "processing"

    status_response = await client.get(
        f"/api/contract-versions/{version_id}/analysis", headers=headers
    )
    assert status_response.json()["analysis_status"] == "completed"

    clauses_response = await client.get(
        f"/api/contract-versions/{version_id}/clauses", headers=headers
    )
    clauses = clauses_response.json()
    assert len(clauses) == 2
    numbers = {c["clause_number"] for c in clauses}
    assert numbers == {"12.3", "12.4"}

    liability_clause = next(c for c in clauses if c["clause_number"] == "12.3")
    assert liability_clause["category"] == "liability"
    assert liability_clause["subcategory"] == "liability_cap"
    assert "20%" in liability_clause["extracted_percentages"]

    indemnity_clause = next(c for c in clauses if c["clause_number"] == "12.4")
    assert indemnity_clause["subcategory"] == "indemnity"

    clause_detail_response = await client.get(f"/api/clauses/{liability_clause['id']}", headers=headers)
    clause_detail = clause_detail_response.json()
    assert len(clause_detail["links"]) >= 1  # liability <-> indemnity category-pattern link

    findings_response = await client.get(
        f"/api/contract-versions/{version_id}/risk-findings", headers=headers
    )
    findings = findings_response.json()
    assert len(findings) >= 2  # one per clause, at least
    for finding in findings:
        assert finding["computed_score"] >= 0
        assert finding["severity"] in ("critical", "high", "medium", "low", "informational")
        assert "final_score" in finding["risk_factors"]

    # The liability clause's risk analysis call should have received the
    # indemnity clause as cross-clause context — verifiable via the fake
    # provider's own call log AND via the persisted finding's related_clauses.
    liability_finding = next(f for f in findings if f["clause_id"] == liability_clause["id"])
    assert "12.4" in liability_finding["related_clauses"]


async def test_review_action_appears_immediately_in_response(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version = await _upload_version(client, headers, contract_id)
    await client.post(f"/api/contract-versions/{version['id']}/analysis", headers=headers)

    findings_response = await client.get(
        f"/api/contract-versions/{version['id']}/risk-findings", headers=headers
    )
    finding_id = findings_response.json()[0]["id"]

    review_response = await client.post(
        f"/api/risk-findings/{finding_id}/review",
        json={"new_status": "marked_for_negotiation", "comment": "Flagging for negotiation."},
        headers=headers,
    )
    assert review_response.status_code == 200
    body = review_response.json()
    assert body["reviewer_status"] == "marked_for_negotiation"
    assert len(body["review_actions"]) == 1
    assert body["review_actions"][0]["comment"] == "Flagging for negotiation."

    # Confirm it persisted, not just reflected in the mutation response.
    detail_response = await client.get(f"/api/risk-findings/{finding_id}", headers=headers)
    assert len(detail_response.json()["review_actions"]) == 1


async def test_rerunning_analysis_does_not_duplicate_clauses_or_findings(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    """Regression test: discovered live against a real Ollama-backed run
    that got re-triggered after a server restart — every clause and
    finding was duplicated because the pipeline only ever appended new
    rows on each run. Also exercised via the UI's "Re-run analysis"
    button on an already-completed version, so this isn't just a
    restart-recovery edge case."""
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version = await _upload_version(client, headers, contract_id)
    version_id = version["id"]

    await client.post(f"/api/contract-versions/{version_id}/analysis", headers=headers)
    clauses_after_first_run = (
        await client.get(f"/api/contract-versions/{version_id}/clauses", headers=headers)
    ).json()
    findings_after_first_run = (
        await client.get(f"/api/contract-versions/{version_id}/risk-findings", headers=headers)
    ).json()
    assert len(clauses_after_first_run) == 2

    await client.post(f"/api/contract-versions/{version_id}/analysis", headers=headers)
    clauses_after_second_run = (
        await client.get(f"/api/contract-versions/{version_id}/clauses", headers=headers)
    ).json()
    findings_after_second_run = (
        await client.get(f"/api/contract-versions/{version_id}/risk-findings", headers=headers)
    ).json()

    assert len(clauses_after_second_run) == len(clauses_after_first_run) == 2
    assert len(findings_after_second_run) == len(findings_after_first_run)


async def test_analysis_reports_progress_and_clears_it_when_done(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    """A local-model run takes over an hour on a real contract, so the status
    endpoint has to say more than "processing". Progress is written as the
    pipeline goes and the stage is cleared on completion."""
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version = await _upload_version(client, headers, contract_id)

    await client.post(f"/api/contract-versions/{version['id']}/analysis", headers=headers)
    status = (
        await client.get(f"/api/contract-versions/{version['id']}/analysis", headers=headers)
    ).json()

    assert status["analysis_status"] == "completed"
    # Cleared on completion so the UI doesn't show a stale stage label.
    assert status["analysis_stage"] is None
    # The totals stay, showing what the run covered.
    assert status["analysis_progress_total"] == 2
    assert status["analysis_progress_current"] == 2

    detail = (await client.get(f"/api/contracts/{contract_id}", headers=headers)).json()
    assert detail["versions"][0]["analysis_progress_total"] == 2


async def test_analysis_rejects_nonexistent_version(client: AsyncClient, registration_payload):
    headers = await _register_and_get_headers(client, registration_payload)
    response = await client.post(
        "/api/contract-versions/does-not-exist/analysis", headers=headers
    )
    assert response.status_code == 400


async def test_loading_the_sample_contract_twice_does_not_duplicate_it(
    client: AsyncClient, registration_payload
):
    """Regression test: each click of "Try the sample contract" used to seed a
    fresh project + contract, filling the Contracts list and Risk Register
    with identical duplicates."""
    headers = await _register_and_get_headers(client, registration_payload)

    first = await client.post("/api/clauserisk/demo/load", headers=headers)
    second = await client.post("/api/clauserisk/demo/load", headers=headers)

    assert first.json()["id"] == second.json()["id"]
    assert len(second.json()["versions"]) == 2

    contracts = (await client.get("/api/contracts", headers=headers)).json()
    assert len([c for c in contracts if c["is_demo"]]) == 1


async def test_org_wide_contracts_list_spans_projects_and_is_tenant_isolated(
    client: AsyncClient, registration_payload
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_a = await _create_project(client, headers)
    project_b = await _create_project(client, headers)
    contract_a = await _create_contract(client, headers, project_a)
    contract_b = await _create_contract(client, headers, project_b)

    response = await client.get("/api/contracts", headers=headers)
    assert response.status_code == 200
    ids = {c["id"] for c in response.json()}
    assert {contract_a, contract_b} <= ids
    # Each row carries its parent project's name, since the project is no
    # longer implied by the URL the way it is for the per-project endpoint.
    assert all("project_name" in c for c in response.json())

    other_headers = await _register_and_get_headers(
        client,
        {
            "email": "other-org-contracts@example.com",
            "password": "SecurePass123",
            "full_name": "Outsider",
            "organization_name": "Outsider Org",
        },
    )
    other_response = await client.get("/api/contracts", headers=other_headers)
    assert other_response.json() == []


async def test_org_wide_risk_register_spans_contracts_and_filters_by_severity(
    client: AsyncClient, registration_payload, clauserisk_fake_provider
):
    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version = await _upload_version(client, headers, contract_id)
    await client.post(f"/api/contract-versions/{version['id']}/analysis", headers=headers)

    response = await client.get("/api/risk-findings", headers=headers)
    assert response.status_code == 200
    findings = response.json()
    assert len(findings) >= 2
    assert all(f["contract_id"] == contract_id for f in findings)
    assert all("contract_name" in f and "clause_number" in f for f in findings)

    severities = {f["severity"] for f in findings}
    target_severity = next(iter(severities))
    filtered = await client.get(
        "/api/risk-findings", params={"severity": target_severity}, headers=headers
    )
    assert all(f["severity"] == target_severity for f in filtered.json())


async def test_interrupted_analysis_is_marked_failed_and_can_be_rerun(
    client: AsyncClient, registration_payload, clauserisk_fake_provider, db_session
):
    """Regression test: a server restart kills the analysis background task
    with the row still reading "processing", and nothing ever moved it again,
    so the contract was permanently stuck behind a spinner with its own
    "Run analysis" button disabled."""
    from app.models.contract import ContractAnalysisStatus, ContractVersion
    from app.services.clauserisk.pipeline import fail_interrupted_analyses

    headers = await _register_and_get_headers(client, registration_payload)
    project_id = await _create_project(client, headers)
    contract_id = await _create_contract(client, headers, project_id)
    version_id = (await _upload_version(client, headers, contract_id))["id"]

    # Simulate the process dying mid-run.
    version = await db_session.get(ContractVersion, version_id)
    version.analysis_status = ContractAnalysisStatus.PROCESSING
    version.analysis_stage = "Analysing clause risk"
    await db_session.commit()

    assert await fail_interrupted_analyses(db_session) == 1

    status = (
        await client.get(f"/api/contract-versions/{version_id}/analysis", headers=headers)
    ).json()
    assert status["analysis_status"] == "failed"
    assert "interrupted" in status["analysis_error"]
    assert status["analysis_stage"] is None

    # The point of failing it rather than leaving it processing: the run is
    # accepted again instead of being refused or stuck behind a disabled
    # button. (A rerun going on to complete is covered by
    # test_rerunning_analysis_does_not_duplicate_clauses_or_findings.)
    db_session.expire_all()
    rerun = await client.post(f"/api/contract-versions/{version_id}/analysis", headers=headers)
    assert rerun.status_code == 200
    assert rerun.json()["analysis_status"] == "processing"
