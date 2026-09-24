"""Shared deterministic-validation primitive: is an AI-cited excerpt
actually present in the source text? Used by both TenderGuard
(app/services/analysis.py) and ClauseRisk (app/services/clauserisk/
pipeline.py) as the backstop against fabricated evidence — an AI
provider's own honesty is never the only thing standing between a
hallucinated quote and something shown to a user as fact.
"""

import re


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def excerpt_is_verifiable(excerpt: str, source_text: str) -> bool:
    if not excerpt or not source_text:
        return False
    return normalize_text(excerpt) in normalize_text(source_text)
