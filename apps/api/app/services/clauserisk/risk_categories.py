"""Configurable clause/risk category taxonomy (brief: "RISK CATEGORIES").

This is code-level configuration, not a DB-backed admin UI — a reasonable
MVP scope decision (see docs/architecture.md's ClauseRisk section)
consistent with how TenderGuard's priority model
(app/services/priority.py) is a tunable lookup table rather than an admin
screen. Moving this into the database (with an org-level override) is a
natural next step if/when categories need to differ per customer.
"""

CATEGORIES: dict[str, list[str]] = {
    "commercial": [
        "payment",
        "retention",
        "advance_payment",
        "price_adjustment",
        "currency",
        "tax",
        "set_off",
        "reimbursement",
        "invoicing",
        "variations",
        "payment_security",
        "audit_rights",
        "pay_when_paid",
    ],
    "schedule": [
        "milestones",
        "delay",
        "liquidated_damages",
        "extension_of_time",
        "force_majeure",
        "delivery",
        "suspension_of_works",
    ],
    "liability": [
        "liability_cap",
        "unlimited_liability",
        "indemnity",
        "consequential_loss",
        "third_party_claims",
        "exclusive_remedies",
        "limitation_period",
        "environmental_liability",
    ],
    "performance": [
        "kpis",
        "performance_guarantees",
        "acceptance",
        "warranty",
        "defects",
        "rework",
        "fitness_for_purpose",
        "design_responsibility",
        "service_levels",
        "title_and_risk",
    ],
    "termination": [
        "termination_for_convenience",
        "termination_for_cause",
        "suspension",
        "demobilization",
        "step_in",
        "term_and_renewal",
    ],
    "insurance": [
        "insurance_policy_requirements",
        "insurance_limits",
        "insurance_deductibles",
        "additional_insured",
    ],
    "compliance": [
        "hse",
        "regulatory",
        "sanctions",
        "anti_bribery",
        "local_content",
        "labor",
        "data_protection",
        "cyber_security",
        "export_control",
    ],
    "contractual": [
        "governing_law",
        "jurisdiction",
        "arbitration",
        "confidentiality",
        "ip",
        "assignment",
        "subcontracting",
        "scope_of_work",
        "order_of_precedence",
        "entire_agreement",
        "notices",
        "change_of_control",
        "exclusivity",
        "non_solicitation",
        "amendment",
    ],
    "operational": [
        "mobilization",
        "equipment",
        "personnel",
        "standby",
        "weather",
        "site_conditions",
        "client_dependencies",
        "npt",
        "backcharges",
    ],
}

ALL_SUBCATEGORIES: set[str] = {sub for subs in CATEGORIES.values() for sub in subs}


def category_for_subcategory(subcategory: str) -> str | None:
    normalized = subcategory.strip().lower().replace(" ", "_").replace("-", "_")
    for category, subs in CATEGORIES.items():
        if normalized in subs:
            return category
    return None


# Cross-clause relationship types the deterministic linker looks for by
# category-pair pattern (brief: "CROSS-CLAUSE ANALYSIS" examples).
CATEGORY_PAIR_LINKS: list[tuple[str, str, str]] = [
    ("liquidated_damages", "milestones", "ld_linked_to_completion"),
    ("liability_cap", "indemnity", "liability_linked_to_indemnity"),
    ("unlimited_liability", "indemnity", "liability_linked_to_indemnity"),
    ("payment", "set_off", "payment_linked_to_setoff"),
    ("termination_for_cause", "payment", "termination_linked_to_payment"),
    ("termination_for_convenience", "payment", "termination_linked_to_payment"),
    ("warranty", "acceptance", "warranty_linked_to_acceptance"),
    ("defects", "acceptance", "warranty_linked_to_acceptance"),
    ("variations", "extension_of_time", "variation_linked_to_time"),
    ("delay", "extension_of_time", "delay_linked_to_time_relief"),
    ("force_majeure", "extension_of_time", "delay_linked_to_time_relief"),
    ("performance_guarantees", "termination_for_cause", "security_linked_to_termination"),
    ("insurance_limits", "indemnity", "indemnity_linked_to_insurance"),
    ("insurance_limits", "liability_cap", "indemnity_linked_to_insurance"),
    ("pay_when_paid", "payment", "payment_linked_to_setoff"),
    ("suspension", "payment", "termination_linked_to_payment"),
    ("service_levels", "termination_for_cause", "sla_linked_to_termination"),
]
