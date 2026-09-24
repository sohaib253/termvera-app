"""A deterministic stand-in for a real AIProvider, used by tests that
exercise the ClauseRisk pipeline end-to-end (segmentation -> extraction
-> cross-linking -> risk analysis -> deterministic validation -> scoring
-> persistence) without a live Ollama/Claude call. Keyword-driven so
different clause text produces different, plausible classifications —
close enough to real model behavior to test the pipeline's plumbing, not
meant to model actual extraction quality (see docs/ai-evaluation.md for
that).
"""

from app.schemas.clauserisk_ai import (
    ClauseExtractionOutput,
    MissingProtectionFinding,
    MissingProtectionsOutput,
    RiskAnalysisOutput,
    RiskFindingCandidate,
)


class FakeClauseRiskProvider:
    name = "fake"

    def __init__(self) -> None:
        self.extract_calls: list[str] = []
        self.risk_calls: list[tuple[str, list[str]]] = []

    async def is_available(self) -> tuple[bool, str | None]:
        return True, None

    async def extract_clause(self, *, clause_text: str, clause_title: str) -> ClauseExtractionOutput:
        self.extract_calls.append(clause_text)
        lowered = clause_text.lower()

        # Checked in this order deliberately: "indemnify ... without limit"
        # should classify as indemnity (the dominant subject), not get
        # swallowed by the more generic "unlimited" keyword check.
        if "indemnif" in lowered:
            subcategory = "indemnity"
        elif "without limit" in lowered or "unlimited" in lowered:
            subcategory = "unlimited_liability"
        elif "liability" in lowered:
            subcategory = "liability_cap"
        elif "liquidated damages" in lowered:
            subcategory = "liquidated_damages"
        elif "milestone" in lowered or "completion" in lowered:
            subcategory = "milestones"
        elif "insurance" in lowered:
            subcategory = "insurance_policy_requirements"
        else:
            subcategory = ""

        amounts = [w for w in _find_dollar_amounts(clause_text)]
        percentages = [w for w in _find_percentages(clause_text)]

        return ClauseExtractionOutput(
            subcategory=subcategory,
            obligations=[clause_text[:60]] if clause_text else [],
            rights=[],
            conditions=[],
            exceptions=[],
            amounts=amounts,
            dates=[],
            percentages=percentages,
            time_periods=[],
            referenced_clauses=[],
            confidence="high",
        )

    async def analyze_clause_risk(
        self, *, clause_text: str, clause_category: str, related_clauses_context: list[str]
    ) -> RiskAnalysisOutput:
        self.risk_calls.append((clause_category, related_clauses_context))
        if not clause_text.strip():
            return RiskAnalysisOutput(findings=[])

        severity_map = {
            "liability": "high",
            "schedule": "medium",
            "commercial": "medium",
        }
        severity_hint = severity_map.get(clause_category, "low")
        excerpt = clause_text.strip().split(".")[0][:80] or clause_text[:40]

        description = f"Fake finding for category {clause_category}."
        if related_clauses_context:
            description += " Cross-clause context was supplied."

        return RiskAnalysisOutput(
            findings=[
                RiskFindingCandidate(
                    risk_type=f"{clause_category}_risk",
                    severity_hint=severity_hint,
                    description=description,
                    contractual_effect="",
                    potential_exposure="",
                    trigger="",
                    affected_party="contractor",
                    uncertainty="explicit",
                    recommended_review_action="Review with commercial team.",
                    evidence_excerpt=excerpt,
                )
            ]
        )

    async def find_missing_protections(
        self, *, contract_summary: str, categories_present: list[str]
    ) -> MissingProtectionsOutput:
        if "insurance" in categories_present:
            return MissingProtectionsOutput(missing_protections=[])
        return MissingProtectionsOutput(
            missing_protections=[
                MissingProtectionFinding(
                    risk_type="no_insurance_clause",
                    category="insurance",
                    severity_hint="medium",
                    description="No insurance clause was identified in this contract.",
                    recommended_review_action="Confirm whether insurance requirements exist elsewhere.",
                )
            ]
        )


def _find_dollar_amounts(text: str) -> list[str]:
    import re

    return re.findall(r"USD\s?[\d,]+(?:\.\d+)?|\$[\d,]+(?:\.\d+)?", text)


def _find_percentages(text: str) -> list[str]:
    import re

    return re.findall(r"\d+(?:\.\d+)?%", text)
