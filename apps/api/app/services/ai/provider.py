from dataclasses import dataclass
from typing import Protocol

from app.schemas.ai import (
    ComplianceAssessmentOutput,
    ExtractedRequirement,
    RequirementExtractionOutput,
)


@dataclass
class PageText:
    page_number: int
    text: str


class AIProviderError(Exception):
    pass


class AIProvider(Protocol):
    name: str

    async def extract_requirements(self, *, pages: list[PageText]) -> RequirementExtractionOutput: ...

    async def assess_requirement(
        self,
        *,
        requirement: ExtractedRequirement,
        document_id: str,
        candidate_pages: list[PageText],
    ) -> ComplianceAssessmentOutput: ...
