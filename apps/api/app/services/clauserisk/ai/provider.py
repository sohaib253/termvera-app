from typing import Protocol

from app.schemas.clauserisk_ai import (
    ClauseExtractionOutput,
    MissingProtectionsOutput,
    RiskAnalysisOutput,
)


class AIProviderError(Exception):
    pass


class AIProvider(Protocol):
    name: str

    async def is_available(self) -> tuple[bool, str | None]:
        """Returns (available, reason_if_not) — a live/cheap check the
        route layer uses to fail fast with a clear message instead of
        partway through a long background pipeline run."""
        ...

    async def extract_clause(self, *, clause_text: str, clause_title: str) -> ClauseExtractionOutput: ...

    async def analyze_clause_risk(
        self,
        *,
        clause_text: str,
        clause_category: str,
        related_clauses_context: list[str],
    ) -> RiskAnalysisOutput: ...

    async def find_missing_protections(
        self, *, contract_summary: str, categories_present: list[str]
    ) -> MissingProtectionsOutput: ...
