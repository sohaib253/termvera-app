"""The built-in brain: reasoning primitives, contract judgement, tender
judgement against expert assessments, and end-to-end runs through the real
pipelines with no fake provider."""

import io
from collections import Counter

import fitz
import pytest
from httpx import AsyncClient

from app.core.paths import SAMPLE_DATA_DIR
from app.services.brain import text as T
from app.services.brain.contract_engine import analyze_clause, classify, extract_clause, missing_protections
from app.services.brain.tender_engine import BidIndex, assess, extract_requirements
from app.services.demo_fixtures import DEMO_REQUIREMENTS
from app.services.sample_content import CONTRACT_CLAUSES
from app.services.text_verification import excerpt_is_verifiable


def _pdf_pages(filename: str) -> list[tuple[int, str]]:
    document = fitz.open(SAMPLE_DATA_DIR / filename)
    pages = [(i + 1, page.get_text()) for i, page in enumerate(document)]
    document.close()
    return pages


def _clause_text(clause) -> str:
    return f"{clause.number} {clause.title}\n{clause.text}"


# ---------------------------------------------------------------- reasoning


@pytest.mark.parametrize(
    "sentence,value,unit,bound",
    [
        (
            "A Bidder whose average TRIR exceeds 0.50 per 200,000 man-hours shall not be considered.",
            0.5,
            "rate",
            "max",
        ),
        ("a limit of not less than USD 10,000,000 per occurrence", 10_000_000, "usd", "min"),
        ("turnover of not less than USD 20 million", 20_000_000, "usd", "min"),
        ("within twenty-one (21) days of receipt", 21, "day", "max"),
        ("a sampling interval of not more than ten (10) seconds", 10, "second", "max"),
        ("a minimum in-country value of forty percent (40%)", 40, "%", "min"),
    ],
)
def test_quantities_read_value_unit_and_comparator(sentence, value, unit, bound):
    q = T.quantities(sentence)[0]
    assert (q.value, q.unit, q.bound) == (value, unit, bound)


def test_sentences_survive_abbreviations_and_decimals():
    parts = T.sentences("Submit Form No. 3 (e.g. the bond). The rate is 2.5% per annum. Done.")
    assert parts == ["Submit Form No. 3 (e.g. the bond).", "The rate is 2.5% per annum.", "Done."]


def test_content_blocks_drop_headings_so_clauses_dont_bleed():
    pages = [
        (
            1,
            "1.2 Experience\nDetails available on request.\n"
            "1.3 Financial Standing\nTurnover was USD 26 million.",
        )
    ]
    sentences = [s for _, block in T.content_blocks(pages) for s in T.sentences(block)]
    assert sentences == ["Details available on request.", "Turnover was USD 26 million."]


# ---------------------------------------------------------------- contract


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Set-Off", "set_off"),
        ("Retention", "retention"),
        ("Liquidated Damages for Delay", "liquidated_damages"),
        ("Limitation of Liability", "liability_cap"),
        ("Indemnity for Personal Injury", "indemnity"),
        ("Pollution Liability", "environmental_liability"),
        ("Force Majeure", "force_majeure"),
        ("Termination for Convenience", "termination_for_convenience"),
        ("Variations", "variations"),
        ("Intellectual Property", "ip"),
        ("Warranty and Defects", "warranty"),
    ],
)
def test_clause_classification(title, expected):
    assert classify(title, "")[0] == expected


def test_contract_findings_are_diverse_and_every_citation_is_verbatim():
    types: Counter[str] = Counter()
    for clause in CONTRACT_CLAUSES:
        text = _clause_text(clause)
        for finding in analyze_clause(text).findings:
            types[finding.risk_type] += 1
            assert excerpt_is_verifiable(finding.evidence_excerpt, text), finding
            assert "[rule " in finding.description
    # The local model collapsed 41 of 61 findings onto one type; the brain
    # must spread across the taxonomy the way a reviewer would.
    assert len(types) >= 30
    assert max(types.values()) <= 3


@pytest.mark.parametrize(
    "number,risk_type,severity",
    [
        ("12.4", "uncapped_liability", "critical"),
        ("12.6", "environmental_liability", "critical"),
        ("5.2", "set_off_rights_one_sided", "high"),
        ("2.4", "variation_claim_time_bar", "high"),
        ("3.4", "standby_rate_gap", "high"),
        ("15.2", "termination_payment_unclear", "high"),
        ("8.2", "liquidated_damages_exposure", "medium"),  # capped, so not high
        ("5.1", "payment_terms_unfavourable", "medium"),  # 45 days
    ],
)
def test_contract_risk_judgements(number, risk_type, severity):
    clause = next(c for c in CONTRACT_CLAUSES if c.number == number)
    findings = {f.risk_type: f.severity_hint for f in analyze_clause(_clause_text(clause)).findings}
    assert findings.get(risk_type) == severity, findings


def test_severity_follows_the_numbers():
    clause = "15.1 Termination for Convenience\nThe Company may terminate for its convenience upon {} notice."
    short = analyze_clause(clause.format("seven (7) days'"))
    long = analyze_clause(clause.format("ninety (90) days'"))
    assert short.findings[0].severity_hint == "critical"
    assert long.findings[0].severity_hint == "medium"


def test_cross_clause_context_aggravates_a_cap():
    cap = (
        "12.3 Limitation of Liability\n"
        "The Contractor's aggregate liability shall not exceed 20% of the Contract Price."
    )
    alone = {f.risk_type: f.severity_hint for f in analyze_clause(cap).findings}
    related = ["[Clause 12.4] The Contractor shall indemnify the Company without limit."]
    linked = {f.risk_type: f for f in analyze_clause(cap, related).findings}
    assert alone["liability_cap_low"] == "low"
    assert linked["liability_cap_low"].severity_hint == "high"
    assert "12.4" in linked["liability_cap_low"].description


def test_extraction_is_verbatim():
    clause = next(c for c in CONTRACT_CLAUSES if c.number == "8.2")
    extracted = extract_clause(_clause_text(clause), clause.title)
    assert "USD 5,000 per day" in extracted.amounts
    assert "10%" in extracted.percentages
    assert extracted.referenced_clauses == ["8.1"]


def test_missing_protections_find_what_is_genuinely_absent():
    found = {
        m.risk_type
        for m in missing_protections("\n".join(c.text for c in CONTRACT_CLAUSES), []).missing_protections
    }
    # The sample contract has no late-payment interest, no contractor
    # suspension right, and no change-in-law relief...
    assert {"late_payment_interest_absent", "suspension_exposure", "regulatory_compliance_burden"} <= found
    # ...but does have a liability cap and a consequential loss exclusion.
    assert "uncapped_liability" not in found
    assert "consequential_loss_exposure" not in found


# ---------------------------------------------------------------- tender


def test_tender_brain_agrees_with_every_expert_assessment():
    """The demo fixtures are hand-written expert judgements on the sample
    tender and bid. The brain must reach the same conclusion on each."""
    requirements = {
        r.source_clause: r for r in extract_requirements(_pdf_pages("offshore-well-testing-tender.pdf"))
    }
    index = BidIndex.build(_pdf_pages("apex-well-services-bid.pdf"))
    disagreements = []
    for fixture in DEMO_REQUIREMENTS:
        expected = fixture["assessment"]["status"]
        expected = "compliant_looking" if expected == "human_verified" else expected
        judgement, _ = assess(requirements[fixture["source_clause"]], index)
        if judgement.status != expected:
            disagreements.append((fixture["source_clause"], judgement.status, expected))
    assert disagreements == []


def test_tender_brain_separates_procedure_and_contract_obligations():
    requirements = {
        r.source_clause: r for r in extract_requirements(_pdf_pages("offshore-well-testing-tender.pdf"))
    }
    index = BidIndex.build(_pdf_pages("apex-well-services-bid.pdf"))
    # Submission deadline: met by submitting on time, not by bid content.
    assert assess(requirements["1.1"], index)[0].status == "not_applicable_pending_verification"
    # Incident reporting during the contract: an obligation, not a bid gap.
    assert assess(requirements["4.3"], index)[0].status == "not_applicable_pending_verification"


# ---------------------------------------------------------------- end to end


async def _headers(client: AsyncClient, payload) -> dict[str, str]:
    token = (await client.post("/api/auth/register", json=payload)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _bytes(filename: str) -> bytes:
    return (SAMPLE_DATA_DIR / filename).read_bytes()


@pytest.mark.asyncio
async def test_brain_runs_the_real_tender_pipeline_end_to_end(
    client: AsyncClient, registration_payload, monkeypatch
):
    from app.services.ai.brain_provider import TenderGuardBrainProvider

    monkeypatch.setattr("app.services.analysis.get_ai_provider", TenderGuardBrainProvider)
    headers = await _headers(client, registration_payload)
    project_id = (await client.post("/api/projects", json={"name": "Brain run"}, headers=headers)).json()[
        "id"
    ]
    for kind, name in (("tender", "offshore-well-testing-tender.pdf"), ("bid", "apex-well-services-bid.pdf")):
        await client.post(
            f"/api/projects/{project_id}/documents",
            headers=headers,
            data={"document_type": kind},
            files={"file": (name, io.BytesIO(_bytes(name)), "application/pdf")},
        )

    assert (await client.post(f"/api/projects/{project_id}/analysis", headers=headers)).status_code == 202
    status = (await client.get(f"/api/projects/{project_id}/analysis", headers=headers)).json()
    assert status["analysis_status"] == "completed", status

    by_clause = {
        r["source_clause"]: r
        for r in (await client.get(f"/api/projects/{project_id}/requirements", headers=headers)).json()
    }
    assert len(by_clause) >= 25
    assert by_clause["8.3"]["assessment"]["status"] == "evidence_not_found"
    assert by_clause["8.3"]["assessment"]["priority"] == "critical"
    assert by_clause["4.2"]["assessment"]["status"] == "potential_non_compliance"
    assert by_clause["2.4"]["assessment"]["status"] == "compliant_looking"


@pytest.mark.asyncio
async def test_brain_runs_the_real_contract_pipeline_end_to_end(
    client: AsyncClient, registration_payload, monkeypatch
):
    from app.services.clauserisk.ai.brain_provider import ClauseRiskBrainProvider

    monkeypatch.setattr(
        "app.services.clauserisk.pipeline.get_clauserisk_ai_provider", ClauseRiskBrainProvider
    )
    headers = await _headers(client, registration_payload)
    project_id = (await client.post("/api/projects", json={"name": "Contract"}, headers=headers)).json()["id"]
    contract_id = (
        await client.post(f"/api/projects/{project_id}/contracts", json={"name": "MSA"}, headers=headers)
    ).json()["id"]
    name = "offshore-well-testing-contract.pdf"
    version_id = (
        await client.post(
            f"/api/contracts/{contract_id}/versions",
            headers=headers,
            data={"version_label": "Original"},
            files={"file": (name, io.BytesIO(_bytes(name)), "application/pdf")},
        )
    ).json()["id"]

    await client.post(f"/api/contract-versions/{version_id}/analysis", headers=headers)
    status = (await client.get(f"/api/contract-versions/{version_id}/analysis", headers=headers)).json()
    assert status["analysis_status"] == "completed", status

    clauses = (await client.get(f"/api/contract-versions/{version_id}/clauses", headers=headers)).json()
    findings = (
        await client.get(f"/api/contract-versions/{version_id}/risk-findings", headers=headers)
    ).json()
    assert len(clauses) == len(CONTRACT_CLAUSES)
    assert len({f["risk_type"] for f in findings}) >= 30
    # Every finding kept its evidence: nothing failed verification.
    assert all(f["evidence"] for f in findings if f["clause_id"])
    assert any(f["severity"] == "critical" for f in findings)


def test_default_factories_return_the_brain():
    """Regression test: the end-to-end tests above patch the factories, so a
    factory that never actually returned the brain went unnoticed until a
    live run failed with "no provider configured"."""
    from app.services.analysis import get_ai_provider
    from app.services.clauserisk.ai import get_clauserisk_ai_provider

    assert type(get_clauserisk_ai_provider()).__name__ == "ClauseRiskBrainProvider"
    assert type(get_ai_provider()).__name__ == "TenderGuardBrainProvider"
