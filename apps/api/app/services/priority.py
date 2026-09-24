"""Documented, configurable priority model (brief §11).

Priority is derived from mandatory status × assessment status only — it is
not a legal or procurement determination, and reviewers can always
override the resulting status/priority through the review endpoint. This
table is intentionally the single place that encodes the rule, so it can
be tuned without touching the assessment pipeline itself.
"""

_TABLE: dict[tuple[str, str], str] = {
    ("mandatory", "evidence_not_found"): "critical",
    ("mandatory", "potential_non_compliance"): "high",
    ("mandatory", "partially_addressed"): "high",
    ("mandatory", "not_applicable_pending_verification"): "medium",
    ("mandatory", "compliant_looking"): "low",
    ("conditional", "evidence_not_found"): "high",
    ("conditional", "potential_non_compliance"): "medium",
    ("conditional", "partially_addressed"): "medium",
    ("conditional", "not_applicable_pending_verification"): "low",
    ("conditional", "compliant_looking"): "low",
    ("indicative", "evidence_not_found"): "medium",
    ("indicative", "potential_non_compliance"): "medium",
    ("indicative", "partially_addressed"): "medium",
    ("indicative", "not_applicable_pending_verification"): "informational",
    ("indicative", "compliant_looking"): "informational",
    ("unclear", "evidence_not_found"): "medium",
    ("unclear", "potential_non_compliance"): "medium",
    ("unclear", "partially_addressed"): "medium",
    ("unclear", "not_applicable_pending_verification"): "medium",
    ("unclear", "compliant_looking"): "low",
}


def compute_priority(mandatory_status: str, assessment_status: str) -> str:
    return _TABLE.get((mandatory_status, assessment_status), "medium")
