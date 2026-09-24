"""Cloud provider option — "Support ... Cloud AI providers later" (brief).
Untested against a live key in this environment; see docs/ai-evaluation.md.
Mirrors app/services/ai/claude_provider.py's TenderGuard implementation."""

import json
import logging

import anthropic
from pydantic import ValidationError

from app.schemas.clauserisk_ai import (
    ClauseExtractionOutput,
    MissingProtectionsOutput,
    RiskAnalysisOutput,
)
from app.services.clauserisk.ai.prompts import (
    CLAUSE_EXTRACTION_VERSION,
    MISSING_PROTECTIONS_VERSION,
    RISK_ANALYSIS_VERSION,
    load_prompt,
)
from app.services.clauserisk.ai.provider import AIProviderError
from app.services.clauserisk.ai.schemas_json import (
    CLAUSE_EXTRACTION_SCHEMA,
    MISSING_PROTECTIONS_SCHEMA,
    RISK_ANALYSIS_SCHEMA,
)

logger = logging.getLogger("clauserisk.ai.claude")


class ClauseRiskClaudeProvider:
    name = "claude"

    def __init__(self, *, api_key: str, model: str = "claude-opus-5") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._extraction_prompt = load_prompt("clause_extraction", CLAUSE_EXTRACTION_VERSION)
        self._risk_prompt = load_prompt("risk_analysis", RISK_ANALYSIS_VERSION)
        self._missing_prompt = load_prompt("missing_protections", MISSING_PROTECTIONS_VERSION)

    async def is_available(self) -> tuple[bool, str | None]:
        return True, None  # API key presence is checked by the factory before construction

    async def extract_clause(self, *, clause_text: str, clause_title: str) -> ClauseExtractionOutput:
        user_content = (
            f"Extract structured data from this contract clause:\n\nTitle: {clause_title}\n\n{clause_text}"
        )
        raw = await self._call(
            system=self._extraction_prompt, user_content=user_content, schema=CLAUSE_EXTRACTION_SCHEMA
        )
        try:
            return ClauseExtractionOutput.model_validate(raw)
        except ValidationError as exc:
            raise AIProviderError(f"Clause extraction output failed validation: {exc}") from exc

    async def analyze_clause_risk(
        self, *, clause_text: str, clause_category: str, related_clauses_context: list[str]
    ) -> RiskAnalysisOutput:
        context_block = ""
        if related_clauses_context:
            joined = "\n\n".join(related_clauses_context)
            context_block = (
                "\n\nRelated clause context (do not treat the primary clause in isolation):\n\n"
                f"{joined}"
            )
        user_content = (
            f"Identify risk findings in this contract clause (category: {clause_category}):\n\n"
            f"{clause_text}{context_block}"
        )
        raw = await self._call(
            system=self._risk_prompt, user_content=user_content, schema=RISK_ANALYSIS_SCHEMA
        )
        try:
            return RiskAnalysisOutput.model_validate(raw)
        except ValidationError as exc:
            raise AIProviderError(f"Risk analysis output failed validation: {exc}") from exc

    async def find_missing_protections(
        self, *, contract_summary: str, categories_present: list[str]
    ) -> MissingProtectionsOutput:
        user_content = (
            f"Categories found in this contract: {', '.join(categories_present) or 'none'}\n\n"
            f"Contract summary: {contract_summary}"
        )
        raw = await self._call(
            system=self._missing_prompt, user_content=user_content, schema=MISSING_PROTECTIONS_SCHEMA
        )
        try:
            return MissingProtectionsOutput.model_validate(raw)
        except ValidationError as exc:
            raise AIProviderError(f"Missing-protections output failed validation: {exc}") from exc

    async def _call(self, *, system: str, user_content: str, schema: dict) -> dict:
        messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": user_content}]
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=4000,
                    system=system,
                    messages=messages,
                    output_config={"format": {"type": "json_schema", "schema": schema}},
                )
            except anthropic.APIStatusError as exc:
                raise AIProviderError(f"Claude API error: {exc}") from exc
            except anthropic.APIConnectionError as exc:
                raise AIProviderError(f"Could not reach the Claude API: {exc}") from exc

            text = next((b.text for b in response.content if b.type == "text"), None)
            if text is None:
                last_error = AIProviderError("Claude response contained no text block.")
            else:
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    last_error = exc
                    messages = messages + [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": (
                                f"That was not valid JSON matching the schema. Error: {exc}. "
                                "Return only valid JSON matching the schema."
                            ),
                        },
                    ]
                    continue
            logger.warning("Claude structured output attempt %d failed: %s", attempt + 1, last_error)

        raise AIProviderError(f"Claude did not return valid structured output: {last_error}")
