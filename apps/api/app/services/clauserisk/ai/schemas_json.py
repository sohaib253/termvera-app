"""Hand-written JSON Schemas for structured AI output.

`category`/`subcategory` are constrained with `enum` (not just a text
description) so Ollama's/Claude's structured-output decoding is forced to
pick a value from app/services/clauserisk/risk_categories.py's taxonomy —
critical, because app/services/clauserisk/risk_engine.py pattern-matches
on exact subcategory strings (e.g. "liability_cap") to compute risk
scores. A free-text category (tried first; see docs/ai-evaluation.md)
produced inconsistent labels like "Financial Liability" that don't match
anything the rule engine or cross-clause linker recognizes.

Other field `description`s are not decorative — empirically, local
models produce dramatically better-grounded output when each array
field's purpose is spelled out ("explicit dates only, not clause
fragments") than with a bare schema. Keep descriptions here in sync with
app/schemas/clauserisk_ai.py's docstrings/Field(...) descriptions; the
Pydantic models re-validate the response regardless, so drift here is
caught deterministically, not trusted blindly.
"""

from app.services.clauserisk.risk_categories import ALL_SUBCATEGORIES, CATEGORIES
from app.services.clauserisk.risk_types import RISK_TYPE_KEYS

_CATEGORY_ENUM = list(CATEGORIES.keys())
_SUBCATEGORY_ENUM = [*sorted(ALL_SUBCATEGORIES), ""]
_RISK_TYPE_ENUM = list(RISK_TYPE_KEYS)

CLAUSE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "subcategory": {
            "type": "string",
            "enum": _SUBCATEGORY_ENUM,
            "description": (
                "The single best-fitting specific label, or empty string if none fit. "
                "The parent category is derived from this automatically."
            ),
        },
        "obligations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit duties owed by a party, each a short paraphrase",
        },
        "rights": {"type": "array", "items": {"type": "string"}},
        "conditions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Conditions that must be met for the clause to apply",
        },
        "exceptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit carve-outs or exceptions stated in the clause",
        },
        "amounts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit monetary amounts only, e.g. 'USD 5,000 per day'",
        },
        "dates": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit calendar dates only, e.g. '30 June 2027'. Not clause fragments.",
        },
        "percentages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit percentage figures only, e.g. '10% of the Contract Price'",
        },
        "time_periods": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit durations only, e.g. '30 days', '12 months'",
        },
        "referenced_clauses": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Other clause numbers explicitly mentioned in this text, e.g. '5.1'. "
                "Never include this clause's own number."
            ),
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "subcategory",
        "obligations",
        "rights",
        "conditions",
        "exceptions",
        "amounts",
        "dates",
        "percentages",
        "time_periods",
        "referenced_clauses",
        "confidence",
    ],
    "additionalProperties": False,
}

RISK_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "description": "Zero or more risk findings. Empty array if the clause presents no notable risk.",
            "items": {
                "type": "object",
                "properties": {
                    "risk_type": {
                        "type": "string",
                        "enum": _RISK_TYPE_ENUM,
                        "description": (
                            "The single best-fitting risk type for this clause. "
                            "Use 'other' only when nothing else fits."
                        ),
                    },
                    "severity_hint": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "informational"],
                    },
                    "description": {"type": "string", "description": "Plain-language risk description"},
                    "contractual_effect": {"type": "string"},
                    "potential_exposure": {"type": "string"},
                    "trigger": {"type": "string"},
                    "affected_party": {
                        "type": "string",
                        "enum": ["contractor", "client", "both", "third_party", "unclear"],
                    },
                    "uncertainty": {
                        "type": "string",
                        "enum": [
                            "explicit",
                            "not_applicable",
                            "not_found",
                            "ambiguous",
                            "conflicting",
                            "requires_review",
                        ],
                    },
                    "recommended_review_action": {"type": "string"},
                    "evidence_excerpt": {
                        "type": "string",
                        "description": (
                            "A short VERBATIM quote copied exactly from the source text, "
                            "no paraphrasing, no ellipses"
                        ),
                    },
                },
                "required": [
                    "risk_type",
                    "severity_hint",
                    "description",
                    "contractual_effect",
                    "potential_exposure",
                    "trigger",
                    "affected_party",
                    "uncertainty",
                    "recommended_review_action",
                    "evidence_excerpt",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

MISSING_PROTECTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "missing_protections": {
            "type": "array",
            "description": (
                "Standard contractual protections that appear absent given the categories "
                "present. Empty array if nothing notable is missing."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "risk_type": {"type": "string", "enum": _RISK_TYPE_ENUM},
                    "category": {"type": "string", "enum": _CATEGORY_ENUM},
                    "severity_hint": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "informational"],
                    },
                    "description": {"type": "string"},
                    "recommended_review_action": {"type": "string"},
                },
                "required": [
                    "risk_type",
                    "category",
                    "severity_hint",
                    "description",
                    "recommended_review_action",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["missing_protections"],
    "additionalProperties": False,
}
