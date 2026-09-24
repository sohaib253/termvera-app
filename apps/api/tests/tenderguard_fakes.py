"""A deterministic stand-in for a real AIProvider, used by tests that
exercise TenderGuard's compliance analysis pipeline end-to-end
(extraction -> evidence matching -> deterministic excerpt verification ->
persistence) without a live Claude call.
"""

from app.schemas.ai import (
    ComplianceAssessmentOutput,
    EvidenceCandidate,
    ExtractedRequirement,
    RequirementExtractionOutput,
)
from app.services.ai.provider import PageText


class FakeTenderGuardProvider:
    name = "fake"

    def __init__(self) -> None:
        self.extract_calls = 0
        self.assess_calls = 0

    async def extract_requirements(self, *, pages: list[PageText]) -> RequirementExtractionOutput:
        self.extract_calls += 1
        requirements = []
        for page in pages:
            snippet = page.text.strip()
            if not snippet:
                continue
            requirements.append(
                ExtractedRequirement(
                    source_page=page.page_number,
                    source_clause=f"{page.page_number}.1",
                    source_excerpt=snippet[:80],
                    title=f"Requirement on page {page.page_number}",
                    normalized_requirement=snippet[:200],
                    category="general",
                    mandatory_status="mandatory",
                )
            )
        return RequirementExtractionOutput(requirements=requirements)

    async def assess_requirement(
        self,
        *,
        requirement: ExtractedRequirement,
        document_id: str,
        candidate_pages: list[PageText],
    ) -> ComplianceAssessmentOutput:
        self.assess_calls += 1
        for page in candidate_pages:
            if requirement.normalized_requirement[:20].lower() in page.text.lower():
                return ComplianceAssessmentOutput(
                    status="compliant_looking",
                    evidence_quality="adequate",
                    assessment_confidence="high",
                    reason="Fake match found in bid text.",
                    requires_human_review=True,
                    evidence=[
                        EvidenceCandidate(
                            document_id=document_id,
                            page_number=page.page_number,
                            excerpt=page.text.strip()[:80],
                            retrieval_method="fake",
                        )
                    ],
                )
        return ComplianceAssessmentOutput(
            status="evidence_not_found",
            evidence_quality="none",
            assessment_confidence="high",
            reason="Fake provider found no matching text in the bid.",
            requires_human_review=True,
            evidence=[],
        )
