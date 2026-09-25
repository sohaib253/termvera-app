"""Factory — the ONLY place in ClauseRisk allowed to know provider names.

Every other module (pipeline.py, routes) talks only to the AIProvider
protocol in app/services/clauserisk/ai/provider.py.
"""

from app.core.config import get_settings
from app.services.clauserisk.ai.provider import AIProvider


def get_clauserisk_ai_provider() -> AIProvider | None:
    settings = get_settings()

    if settings.clauserisk_ai_provider == "brain":
        from app.services.clauserisk.ai.brain_provider import ClauseRiskBrainProvider

        return ClauseRiskBrainProvider()

    if settings.clauserisk_ai_provider == "ollama":
        from app.services.clauserisk.ai.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    if settings.clauserisk_ai_provider == "claude":
        if not settings.anthropic_api_key:
            return None
        from app.services.clauserisk.ai.claude_provider import ClauseRiskClaudeProvider

        return ClauseRiskClaudeProvider(
            api_key=settings.anthropic_api_key, model=settings.anthropic_model
        )

    return None
