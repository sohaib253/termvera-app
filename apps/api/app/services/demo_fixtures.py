"""Precomputed demo requirements, evidence, and assessments for the sample
tender project.

Every `source_excerpt` and evidence `excerpt` here is taken directly from
app/services/sample_content.py, which is also what scripts/
generate_sample_data.py renders the PDFs from. That makes the demo's core
claim - every citation is a verbatim substring of the real extracted
document text - true by construction rather than by manual re-checking.
Page numbers come from sample_data/manifest.json, written by the same
generator, so re-rendering the PDFs cannot silently invalidate a citation.

This is section 14 of the product brief's "sample results": precomputed,
clearly labelled, and deliberately NOT a live AI call. See
docs/architecture.md Phase 6 for why it is a seeding path separate from
the real AIProvider used by POST /api/projects/{id}/analysis.

The findings below are the interesting ones a bid manager would actually
argue about: a missing mandatory form, a certification gap, a safety
statistic that fails a stated threshold, an under-capacity item, and two
commercial terms the bidder tried to re-trade.
"""

import json
from typing import Any

from app.core.paths import SAMPLE_DATA_DIR as _SAMPLE_DATA_DIR
from app.services.sample_content import BID_SECTIONS, TENDER_SECTIONS

TENDER_FILENAME = "offshore-well-testing-tender.pdf"
BID_FILENAME = "apex-well-services-bid.pdf"
MANIFEST_FILENAME = "manifest.json"

_TENDER_CLAUSES = {c.number: c for s in TENDER_SECTIONS for c in s.clauses}
_BID_CLAUSES = {c.number: c for s in BID_SECTIONS for c in s.clauses}


def _manifest() -> dict[str, dict[str, int]]:
    path = _SAMPLE_DATA_DIR / MANIFEST_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run apps/api/scripts/generate_sample_data.py to "
            "regenerate the sample PDFs and their page manifest."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def tender_page(clause_number: str) -> int:
    return _manifest()[TENDER_FILENAME][clause_number]


def bid_page(clause_number: str) -> int:
    return _manifest()[BID_FILENAME][clause_number]


def tender_text(clause_number: str) -> str:
    return _TENDER_CLAUSES[clause_number].text


def bid_text(clause_number: str) -> str:
    return _BID_CLAUSES[clause_number].text


def _requirement(
    *,
    tender_clause: str,
    title: str,
    normalized: str,
    category: str,
    mandatory_status: str,
    required_evidence: str,
    assessment: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    conditions: str | None = None,
    extraction_uncertain: bool = False,
    review_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": f"req-{tender_clause}",
        "source_page": tender_page(tender_clause),
        "source_clause": tender_clause,
        "source_excerpt": tender_text(tender_clause),
        "title": title,
        "normalized_requirement": normalized,
        "category": category,
        "mandatory_status": mandatory_status,
        "conditions": conditions,
        "required_evidence": required_evidence,
        "extraction_uncertain": extraction_uncertain,
        "evidence": evidence or [],
        "assessment": assessment,
        "review_action": review_action,
    }


def _evidence(
    bid_clause: str,
    *,
    evidence_type: str,
    relevance_note: str,
    potential_conflict: str | None = None,
    retrieval_method: str = "keyword+semantic",
) -> dict[str, Any]:
    return {
        "page": bid_page(bid_clause),
        "excerpt": bid_text(bid_clause),
        "retrieval_method": retrieval_method,
        "evidence_type": evidence_type,
        "relevance_note": relevance_note,
        "potential_conflict": potential_conflict,
    }


DEMO_REQUIREMENTS: list[dict[str, Any]] = [
    _requirement(
        tender_clause="3.1",
        title="Minimum offshore well testing experience",
        normalized=(
            "Bidder must have completed at least 3 offshore well testing projects in the last "
            "5 years, each involving flow testing of at least one well, and must list each "
            "qualifying project with client name, well count, and completion date."
        ),
        category="Experience & Track Record",
        mandatory_status="mandatory",
        required_evidence=(
            "List of at least 3 qualifying offshore well testing projects with client name, "
            "well count, and completion date."
        ),
        evidence=[
            _evidence(
                "1.2",
                evidence_type="narrative statement",
                relevance_note=(
                    "Asserts relevant experience but names no projects, clients, well counts, "
                    "or completion dates, so the three-project threshold cannot be checked."
                ),
            ),
            _evidence(
                "1.1",
                evidence_type="company profile",
                relevance_note=(
                    "Years of operating history is not the same as the qualifying project count "
                    "the clause asks for."
                ),
            ),
        ],
        assessment={
            "status": "partially_addressed",
            "evidence_quality": "insufficient",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "The bid asserts relevant offshore experience but does not list any qualifying "
                "project with the client name, well count, and completion date the clause "
                "requires. Compliance cannot be established from the submitted text."
            ),
            "missing_information": [
                "Named list of at least 3 qualifying offshore well testing projects",
                "Client name for each project",
                "Number of wells tested per project",
                "Completion date for each project",
            ],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="3.2",
        title="Minimum average annual turnover",
        normalized=(
            "Bidder must show average annual turnover of at least USD 20 million over the last "
            "3 audited financial years and submit audited financial statements for each year."
        ),
        category="Financial Standing",
        mandatory_status="mandatory",
        required_evidence="Audited financial statements for the last 3 financial years.",
        evidence=[
            _evidence(
                "1.3",
                evidence_type="financial statement",
                relevance_note=(
                    "States USD 26.4 million average turnover against a USD 20 million "
                    "threshold, and refers to audited statements attached as an appendix."
                ),
            )
        ],
        assessment={
            "status": "compliant_looking",
            "evidence_quality": "adequate",
            "assessment_confidence": "high",
            "priority": "medium",
            "reason": (
                "Stated average turnover of USD 26.4 million exceeds the USD 20 million "
                "threshold and the bid references audited statements for all three years. The "
                "appendix itself is not part of the submitted text, so the figures have not "
                "been verified against the statements."
            ),
            "missing_information": [
                "Appendix 2 audited financial statements were not provided for verification"
            ],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="3.3",
        title="ISO 9001, 14001 and 45001 certification",
        normalized=(
            "Bidder must hold current ISO 9001, ISO 14001, and ISO 45001 certification and "
            "include copies of all three certificates in Envelope 1."
        ),
        category="Certification & Compliance",
        mandatory_status="mandatory",
        required_evidence="Copies of current ISO 9001, ISO 14001 and ISO 45001 certificates.",
        evidence=[
            _evidence(
                "2.1",
                evidence_type="certification statement",
                relevance_note=(
                    "Confirms ISO 9001 and ISO 45001 but states ISO 14001 is not yet held, with "
                    "an audit expected in Q3 2026 - after the tender decision."
                ),
                potential_conflict=(
                    "Clause 3.3 requires current certification to all three standards; the bid "
                    "confirms only two."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "The bid states ISO 14001 certification is still being worked towards, with an "
                "audit expected in Q3 2026. Clause 3.3 requires current certification to all "
                "three standards at submission, so this is a clear gap rather than an "
                "evidential one."
            ),
            "missing_information": ["Current ISO 14001 certificate"],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="4.2",
        title="Three-year average TRIR below 0.50",
        normalized=(
            "Bidder must report TRIR for each of the last 3 calendar years; a three-year "
            "average TRIR above 0.50 per 200,000 man-hours disqualifies the bidder from award."
        ),
        category="HSE",
        mandatory_status="mandatory",
        required_evidence="TRIR figures for each of the last 3 calendar years.",
        evidence=[
            _evidence(
                "3.2",
                evidence_type="safety statistic",
                relevance_note=(
                    "Reports a three-year average TRIR of 0.71 against a stated maximum of "
                    "0.50, which the clause treats as grounds for exclusion from award."
                ),
                potential_conflict=(
                    "Numerical mismatch: bid states 0.71, tender sets a maximum of 0.50."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "The reported three-year average TRIR of 0.71 exceeds the 0.50 threshold in "
                "Clause 4.2. The figure is clearly stated in the bid, so this is a substantive "
                "failure against a stated screening criterion, not an evidence gap."
            ),
            "missing_information": [
                "Year-by-year TRIR breakdown (only a three-year average was given)"
            ],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="4.1",
        title="Documented HSE management system",
        normalized=(
            "Bidder must operate a documented HSE management system and submit the manual or a "
            "detailed summary of its contents with the tender."
        ),
        category="HSE",
        mandatory_status="mandatory",
        required_evidence="HSE management system manual or detailed summary.",
        evidence=[
            _evidence(
                "3.1",
                evidence_type="management system description",
                relevance_note=(
                    "Describes a documented system aligned to ISO 45001 and refers to a summary "
                    "attached as an appendix."
                ),
            )
        ],
        assessment={
            "status": "compliant_looking",
            "evidence_quality": "adequate",
            "assessment_confidence": "medium",
            "priority": "medium",
            "reason": (
                "The bid describes a documented HSE management system and names its core "
                "elements. The referenced appendix summary is outside the submitted text, so "
                "the depth of the system has not been assessed."
            ),
            "missing_information": ["Appendix 4 HSE system summary was not provided"],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="5.2",
        title="Test separator minimum capacity",
        normalized=(
            "The test separator must handle at least 10,000 barrels of liquid per day and 50 "
            "MMscf of gas per day."
        ),
        category="Technical",
        mandatory_status="mandatory",
        required_evidence="Separator capacity specification.",
        evidence=[
            _evidence(
                "4.2",
                evidence_type="equipment specification",
                relevance_note=(
                    "Gas capacity of 50 MMscf/d meets the requirement, but liquid capacity of "
                    "8,000 bbl/d falls short of the 10,000 bbl/d minimum."
                ),
                potential_conflict=(
                    "Numerical mismatch: bid offers 8,000 bbl/d against a 10,000 bbl/d minimum."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "high",
            "reason": (
                "The proposed separator's liquid handling capacity of 8,000 barrels per day is "
                "below the 10,000 barrels per day minimum in Clause 5.2. Gas capacity meets the "
                "requirement, so only the liquid side is deficient."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="6.2",
        title="Acceptance of 45-day payment terms",
        normalized=(
            "Bidder must confirm acceptance of payment within 45 days of a valid invoice, "
            "without qualification."
        ),
        category="Commercial",
        mandatory_status="mandatory",
        required_evidence="Unqualified confirmation of the 45-day payment term.",
        evidence=[
            _evidence(
                "5.2",
                evidence_type="commercial qualification",
                relevance_note=(
                    "The bid proposes 30-day payment and asks for the tender's 45-day term to "
                    "be amended, which is the qualification Clause 6.2 forbids."
                ),
                potential_conflict=(
                    "Clause 9.2 lists qualifying the Company's payment terms as grounds for "
                    "disqualification."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "high",
            "reason": (
                "Clause 6.2 requires unqualified acceptance of 45-day payment terms. The bid "
                "instead proposes 30 days and asks for the contract to be amended, which "
                "Clause 9.2 identifies as a ground for disqualification."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="6.3",
        title="Firm pricing for 24 months",
        normalized=(
            "All prices must be quoted in USD and remain firm and fixed for the first 24 months "
            "of the contract term."
        ),
        category="Commercial",
        mandatory_status="mandatory",
        required_evidence="Confirmation of USD pricing firm for 24 months.",
        evidence=[
            _evidence(
                "5.3",
                evidence_type="commercial qualification",
                relevance_note=(
                    "Offers firm pricing for 18 months against the 24 months required, then "
                    "proposes indexation."
                ),
                potential_conflict=(
                    "Numerical mismatch: 18 months offered against 24 months required."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "high",
            "reason": (
                "The bid holds prices firm for 18 months and proposes annual indexation "
                "thereafter, short of the 24-month firm period required by Clause 6.3."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="7.1",
        title="Insurance limits of USD 10,000,000 per occurrence",
        normalized=(
            "Contractor must carry employer's liability and third-party liability insurance, "
            "each with a limit of at least USD 10,000,000 per occurrence."
        ),
        category="Insurance & Liability",
        mandatory_status="mandatory",
        required_evidence="Certificates of insurance showing both limits.",
        evidence=[
            _evidence(
                "6.1",
                evidence_type="insurance statement",
                relevance_note=(
                    "Employer's liability meets the USD 10,000,000 limit, but third-party "
                    "liability is stated at USD 5,000,000, half the required amount."
                ),
                potential_conflict=(
                    "Numerical mismatch on third-party liability: USD 5,000,000 offered against "
                    "USD 10,000,000 required."
                ),
            )
        ],
        assessment={
            "status": "potential_non_compliance",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "Third-party liability cover of USD 5,000,000 is half the USD 10,000,000 per "
                "occurrence limit required by Clause 7.1. Employer's liability cover meets the "
                "requirement."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="8.3",
        title="Form C - HSE statistics return (mandatory)",
        normalized=(
            "Bidder must submit Form C stating lost time injuries, recordable incidents, and "
            "man-hours worked for each of the last 3 calendar years. A tender without Form C is "
            "rejected."
        ),
        category="Mandatory Forms",
        mandatory_status="mandatory",
        required_evidence="Completed Form C covering the last 3 calendar years.",
        evidence=[
            _evidence(
                "7.1",
                evidence_type="forms schedule",
                relevance_note=(
                    "The list of enclosed forms names Forms A, B, D and E. Form C is absent "
                    "from the enclosure list."
                ),
                potential_conflict=(
                    "Clause 8.3 states a tender submitted without Form C will be rejected."
                ),
            )
        ],
        assessment={
            "status": "evidence_not_found",
            "evidence_quality": "none",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "Form C was not located in the submitted bid. The bid's own schedule of "
                "enclosed forms lists A, B, D and E only. Clause 8.3 makes Form C mandatory and "
                "its omission a ground for rejection."
            ),
            "missing_information": [
                "Form C - HSE statistics return",
                "Lost time injuries per year for the last 3 years",
                "Man-hours worked per year for the last 3 years",
            ],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="3.4",
        title="Minimum 40% in-country value",
        normalized=(
            "Bidder must state its in-country value percentage and commit to at least 40% of "
            "total contract price spent in-country."
        ),
        category="Local Content",
        mandatory_status="mandatory",
        required_evidence="Stated in-country value percentage and Form E.",
        evidence=[
            _evidence(
                "2.2",
                evidence_type="commitment statement",
                relevance_note=(
                    "Commits to 42% in-country value against a 40% minimum, identifies the "
                    "components, and confirms Form E is attached."
                ),
            )
        ],
        assessment={
            "status": "human_verified",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "low",
            "reason": (
                "The bid commits to 42% in-country value against the 40% minimum and breaks "
                "down how the figure is made up. Verified against Form E by the reviewer."
            ),
            "missing_information": [],
            "requires_human_review": False,
            "reviewer_status": "reviewed",
        },
        review_action={
            "previous_status": "compliant_looking",
            "new_status": "human_verified",
            "comment": (
                "Checked Form E against the stated 42%. Breakdown is consistent and the "
                "commitment is unqualified. Closing this one out."
            ),
        },
    ),
    _requirement(
        tender_clause="1.2",
        title="Minimum 120-day tender validity",
        normalized=(
            "Each tender must remain valid for at least 120 days from the submission deadline."
        ),
        category="Tender Administration",
        mandatory_status="mandatory",
        required_evidence="Statement of bid validity period.",
        evidence=[
            _evidence(
                "5.4",
                evidence_type="validity statement",
                relevance_note="States 120 days validity, matching the required minimum exactly.",
            )
        ],
        assessment={
            "status": "compliant_looking",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "low",
            "reason": (
                "The bid states a validity period of 120 days from the submission deadline, "
                "matching the minimum in Clause 1.2."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="1.5",
        title="Bid bond of USD 250,000",
        normalized=(
            "Bidder must provide a USD 250,000 bid bond from an acceptable bank, valid for 30 "
            "days beyond the tender validity period."
        ),
        category="Tender Administration",
        mandatory_status="mandatory",
        required_evidence="Bid bond instrument or issuing bank confirmation.",
        evidence=[],
        assessment={
            "status": "evidence_not_found",
            "evidence_quality": "none",
            "assessment_confidence": "high",
            "priority": "critical",
            "reason": (
                "No reference to a bid bond was located anywhere in the submitted bid. The "
                "requirement may have been satisfied by a separate instrument outside this "
                "document, which a reviewer needs to confirm before the tender is scored."
            ),
            "missing_information": [
                "Bid bond instrument",
                "Issuing bank name",
                "Bond validity period",
            ],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="2.4",
        title="Mobilisation within 21 days of call-off",
        normalized=(
            "Contractor must fully mobilise equipment and personnel to the offshore location "
            "within 21 days of the written call-off notice."
        ),
        category="Technical",
        mandatory_status="mandatory",
        required_evidence="Stated mobilisation period.",
        evidence=[
            _evidence(
                "4.5",
                evidence_type="commitment statement",
                relevance_note="Commits to 21 days, matching the requirement exactly.",
            )
        ],
        assessment={
            "status": "compliant_looking",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "medium",
            "reason": (
                "The bid commits to mobilisation within 21 days of the written call-off notice, "
                "matching Clause 2.4."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
    _requirement(
        tender_clause="5.3",
        title="Real-time data acquisition and 24-hour delivery",
        normalized=(
            "Contractor must provide real-time data acquisition at intervals of 10 seconds or "
            "less and deliver the complete dataset within 24 hours of each test."
        ),
        category="Technical",
        mandatory_status="mandatory",
        required_evidence="Sampling interval and dataset delivery commitment.",
        evidence=[
            _evidence(
                "4.4",
                evidence_type="technical commitment",
                relevance_note=(
                    "Offers a 5-second sampling interval, better than the 10-second maximum, "
                    "and matches the 24-hour delivery commitment."
                ),
            )
        ],
        assessment={
            "status": "compliant_looking",
            "evidence_quality": "strong",
            "assessment_confidence": "high",
            "priority": "low",
            "reason": (
                "The offered 5-second sampling interval exceeds the requirement of no more than "
                "10 seconds, and the 24-hour dataset delivery commitment matches Clause 5.3."
            ),
            "missing_information": [],
            "requires_human_review": True,
            "reviewer_status": "unreviewed",
        },
    ),
]
