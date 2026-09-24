import json
import logging

import httpx
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

logger = logging.getLogger("clauserisk.ai.ollama")


class OllamaProvider:
    name = "ollama"

    def __init__(self, *, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._extraction_prompt = load_prompt("clause_extraction", CLAUSE_EXTRACTION_VERSION)
        self._risk_prompt = load_prompt("risk_analysis", RISK_ANALYSIS_VERSION)
        self._missing_prompt = load_prompt("missing_protections", MISSING_PROTECTIONS_VERSION)

    async def is_available(self) -> tuple[bool, str | None]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                tags = response.json()
        except Exception as exc:
            return False, f"Could not reach Ollama at {self._base_url}: {exc}"

        model_names = {m.get("name") for m in tags.get("models", [])}
        if self._model not in model_names:
            return False, (
                f"Ollama is reachable but model '{self._model}' is not pulled. "
                f"Run: ollama pull {self._model}"
            )
        return True, None

    async def extract_clause(self, *, clause_text: str, clause_title: str) -> ClauseExtractionOutput:
        user_content = (
            f"Extract structured data from this contract clause:\n\nTitle: {clause_title}\n\n{clause_text}"
        )
        raw = await self._chat(
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
        raw = await self._chat(
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
        raw = await self._chat(
            system=self._missing_prompt, user_content=user_content, schema=MISSING_PROTECTIONS_SCHEMA
        )
        try:
            return MissingProtectionsOutput.model_validate(raw)
        except ValidationError as exc:
            raise AIProviderError(f"Missing-protections output failed validation: {exc}") from exc

    async def _chat(self, *, system: str, user_content: str, schema: dict) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=300.0) as client:
            for attempt in range(2):
                try:
                    response = await client.post(
                        f"{self._base_url}/api/chat",
                        json={
                            "model": self._model,
                            "messages": messages,
                            "stream": False,
                            "format": schema,
                            "options": {"temperature": 0.1},
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise AIProviderError(f"Ollama request failed: {exc}") from exc

                data = response.json()
                content = data.get("message", {}).get("content")
                if not content:
                    last_error = AIProviderError("Ollama response contained no content.")
                else:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as exc:
                        last_error = exc
                        messages = messages + [
                            {"role": "assistant", "content": content},
                            {
                                "role": "user",
                                "content": (
                                    f"That was not valid JSON matching the schema. Error: {exc}. "
                                    "Return only valid JSON matching the schema."
                                ),
                            },
                        ]
                        continue
                logger.warning("Ollama structured output attempt %d failed: %s", attempt + 1, last_error)

        raise AIProviderError(f"Ollama did not return valid structured output: {last_error}")
