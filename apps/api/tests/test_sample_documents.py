"""Guards the sample documents' core claim: every citation the demo shows a
user is a real substring of the real extracted PDF text, on the page it says.

If someone edits sample_content.py without re-running
scripts/generate_sample_data.py, these tests fail rather than the product
quietly showing a citation that isn't in the document.
"""

from pathlib import Path

import fitz
import pytest

from app.services import demo_fixtures
from app.services.demo_fixtures import BID_FILENAME, DEMO_REQUIREMENTS, TENDER_FILENAME
from app.services.sample_content import (
    AMENDMENT_CLAUSES,
    BID_SECTIONS,
    CONTRACT_CLAUSES,
    TENDER_SECTIONS,
)
from app.services.text_verification import excerpt_is_verifiable

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

CONTRACT_FILENAME = "offshore-well-testing-contract.pdf"
AMENDMENT_FILENAME = "offshore-well-testing-contract-amendment-1.pdf"


def _page_texts(filename: str) -> dict[int, str]:
    path = SAMPLE_DATA_DIR / filename
    assert path.exists(), f"{filename} missing. Run scripts/generate_sample_data.py."
    document = fitz.open(path)
    pages = {index + 1: page.get_text() for index, page in enumerate(document)}
    document.close()
    return pages


@pytest.mark.parametrize(
    "filename,clauses",
    [
        (TENDER_FILENAME, [c for s in TENDER_SECTIONS for c in s.clauses]),
        (BID_FILENAME, [c for s in BID_SECTIONS for c in s.clauses]),
        (CONTRACT_FILENAME, list(CONTRACT_CLAUSES)),
        (AMENDMENT_FILENAME, list(AMENDMENT_CLAUSES)),
    ],
)
def test_every_clause_is_extractable_verbatim(filename, clauses):
    pages = _page_texts(filename)
    whole_document = "\n".join(pages.values())
    for clause in clauses:
        assert excerpt_is_verifiable(clause.text, whole_document), (
            f"{filename} clause {clause.number} is not extractable verbatim"
        )


def test_demo_citations_land_on_the_page_they_claim():
    tender_pages = _page_texts(TENDER_FILENAME)
    bid_pages = _page_texts(BID_FILENAME)

    for requirement in DEMO_REQUIREMENTS:
        page = requirement["source_page"]
        assert excerpt_is_verifiable(requirement["source_excerpt"], tender_pages[page]), (
            f"requirement {requirement['key']} excerpt is not on tender page {page}"
        )
        for evidence in requirement["evidence"]:
            evidence_page = evidence["page"]
            assert excerpt_is_verifiable(evidence["excerpt"], bid_pages[evidence_page]), (
                f"{requirement['key']} evidence is not on bid page {evidence_page}"
            )


def test_manifest_covers_every_clause_the_fixtures_reference():
    manifest = demo_fixtures._manifest()
    for requirement in DEMO_REQUIREMENTS:
        assert requirement["source_clause"] in manifest[TENDER_FILENAME]


@pytest.mark.asyncio
async def test_samples_can_be_listed_and_downloaded(client, registration_payload):
    register = await client.post("/api/auth/register", json=registration_payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    listing = await client.get("/api/samples", headers=headers)
    assert listing.status_code == 200
    samples = listing.json()
    assert {s["key"] for s in samples} == {"tender", "bid", "contract", "amendment"}
    assert all(s["size_bytes"] > 0 for s in samples)

    download = await client.get("/api/samples/contract/file", headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_sample_download_requires_auth_and_a_known_key(client, registration_payload):
    assert (await client.get("/api/samples/contract/file")).status_code == 401

    register = await client.post("/api/auth/register", json=registration_payload)
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    # Keys are an allow-list, so a traversal attempt is simply unknown.
    assert (await client.get("/api/samples/..%2F..%2Fsecret/file", headers=headers)).status_code == 404


def test_sample_documents_are_substantial_enough_to_be_realistic():
    """A two-paragraph "tender" doesn't demonstrate anything a bid manager
    recognises. These floors are deliberately loose - they catch a
    regeneration that silently produced a stub, not a content edit."""
    tender_pages = _page_texts(TENDER_FILENAME)
    contract_pages = _page_texts(CONTRACT_FILENAME)

    assert len(tender_pages) >= 3
    assert len(contract_pages) >= 3
    assert len([c for s in TENDER_SECTIONS for c in s.clauses]) >= 25
    assert len(CONTRACT_CLAUSES) >= 25
