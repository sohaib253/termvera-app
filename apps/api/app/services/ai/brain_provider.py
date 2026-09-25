"""TenderGuard provider backed by the built-in rule engine (app/services/brain).

Implements the same AIProvider protocol as ClaudeProvider. The bid index is
built once per set of bid pages and reused for every requirement in the run,
since the pipeline passes the same page list to each assessment.
"""

from app.schemas.ai import (
    ComplianceAssessmentOutput,
    ExtractedRequirement,
    RequirementExtractionOutput,
)
from app.services.ai.provider import PageText
from app.services.brain import tender_engine


class TenderGuardBrainProvider:
    name = "tenderguard-brain"

    def __init__(self) -> None:
        self._indexes: dict[int, tender_engine.BidIndex] = {}

    async def extract_requirements(self, *, pages: list[PageText]) -> RequirementExtractionOutput:
        return RequirementExtractionOutput(
            requirements=tender_engine.extract_requirements([(p.page_number, p.text) for p in pages])
        )

    async def assess_requirement(
        self,
        *,
        requirement: ExtractedRequirement,
        document_id: str,
        candidate_pages: list[PageText],
    ) -> ComplianceAssessmentOutput:
        key = id(candidate_pages)
        index = self._indexes.get(key)
        if index is None:
            index = tender_engine.BidIndex.build([(p.page_number, p.text) for p in candidate_pages])
            self._indexes[key] = index
        judgement, _ = tender_engine.assess(requirement, index)
        return tender_engine.to_output(judgement, index, document_id, requirement.category)
