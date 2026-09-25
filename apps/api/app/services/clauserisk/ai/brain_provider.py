"""ClauseRisk provider backed by the built-in rule engine (app/services/brain).

Implements the same AIProvider protocol as the Ollama and Claude providers,
so the pipeline cannot tell the difference. The one piece of state: clause
texts seen during extraction are kept so the contract-wide "missing
protections" check can read the whole contract. The factory creates a
fresh instance per analysis run, so this never leaks between contracts.
"""

from app.schemas.clauserisk_ai import (
    ClauseExtractionOutput,
    MissingProtectionsOutput,
    RiskAnalysisOutput,
)
from app.services.brain import contract_engine


class ClauseRiskBrainProvider:
    name = "tenderguard-brain"

    def __init__(self) -> None:
        self._clause_texts: list[str] = []

    async def is_available(self) -> tuple[bool, str | None]:
        return True, None

    async def extract_clause(self, *, clause_text: str, clause_title: str) -> ClauseExtractionOutput:
        self._clause_texts.append(clause_text)
        return contract_engine.extract_clause(clause_text, clause_title)

    async def analyze_clause_risk(
        self, *, clause_text: str, clause_category: str, related_clauses_context: list[str]
    ) -> RiskAnalysisOutput:
        return contract_engine.analyze_clause(clause_text, related_clauses_context)

    async def find_missing_protections(
        self, *, contract_summary: str, categories_present: list[str]
    ) -> MissingProtectionsOutput:
        return contract_engine.missing_protections("\n".join(self._clause_texts), categories_present)
