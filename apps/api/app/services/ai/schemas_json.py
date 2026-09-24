"""Hand-written JSON Schemas for Claude structured output.

Written by hand (not derived from the Pydantic models' `.model_json_schema()`)
so the shape sent to the API stays flat and predictable — no `$defs`/`$ref`
indirection to worry about. Keep these in sync with app/schemas/ai.py; the
Pydantic models re-validate the response afterward regardless, so a drift
here is caught deterministically, not trusted blindly.
"""

REQUIREMENT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_page": {"type": "integer"},
                    "source_clause": {"type": ["string", "null"]},
                    "source_excerpt": {"type": "string"},
                    "title": {"type": "string"},
                    "normalized_requirement": {"type": "string"},
                    "category": {"type": "string"},
                    "mandatory_status": {
                        "type": "string",
                        "enum": ["mandatory", "conditional", "indicative", "unclear"],
                    },
                    "conditions": {"type": ["string", "null"]},
                    "required_evidence": {"type": ["string", "null"]},
                    "extraction_uncertain": {"type": "boolean"},
                },
                "required": [
                    "source_page",
                    "source_clause",
                    "source_excerpt",
                    "title",
                    "normalized_requirement",
                    "category",
                    "mandatory_status",
                    "conditions",
                    "required_evidence",
                    "extraction_uncertain",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["requirements"],
    "additionalProperties": False,
}

COMPLIANCE_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "compliant_looking",
                "partially_addressed",
                "evidence_not_found",
                "potential_non_compliance",
                "not_applicable_pending_verification",
            ],
        },
        "evidence_quality": {
            "type": "string",
            "enum": ["strong", "adequate", "insufficient", "none", "unknown"],
        },
        "assessment_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "requires_human_review": {"type": "boolean"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "page_number": {"type": "integer"},
                    "excerpt": {"type": "string"},
                    "retrieval_method": {"type": "string"},
                    "evidence_type": {"type": ["string", "null"]},
                    "relevance_note": {"type": ["string", "null"]},
                    "potential_conflict": {"type": ["string", "null"]},
                },
                "required": [
                    "document_id",
                    "page_number",
                    "excerpt",
                    "retrieval_method",
                    "evidence_type",
                    "relevance_note",
                    "potential_conflict",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "status",
        "evidence_quality",
        "assessment_confidence",
        "reason",
        "missing_information",
        "requires_human_review",
        "evidence",
    ],
    "additionalProperties": False,
}
