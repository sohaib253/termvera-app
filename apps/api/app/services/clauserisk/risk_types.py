"""Curated taxonomy of commercial contract risk types.

Why this exists: `risk_type` was originally a free-text AI field with only
a description to guide it. Against a local 7B model that produced values
like "explicit", "uncertainty", and "potential exposure" — the model was
copying neighbouring field names and enum values straight into the
free-text slot, so the Risk Register's most important column read as
nonsense to a contract manager.

The fix is the same one that made `subcategory` reliable (see
schemas_json.py's module docstring): constrain the output with an `enum`
so decoding cannot produce anything outside the taxonomy, then map to a
human label for display. `normalize_risk_type` is the deterministic
backstop for providers that don't enforce the enum, and for the local
model's occasional near-miss.
"""

# key -> label shown to a reviewer. Keys are stable; labels are display-only.
RISK_TYPES: dict[str, str] = {
    # Liability
    "uncapped_liability": "Uncapped liability",
    "liability_cap_low": "Liability cap may be inadequate",
    "broad_indemnity": "Broad indemnity obligation",
    "consequential_loss_exposure": "Consequential loss exposure",
    "third_party_claim_exposure": "Third-party claim exposure",
    # Commercial
    "payment_terms_unfavourable": "Unfavourable payment terms",
    "payment_security_gap": "No payment security",
    "retention_exposure": "Retention exposure",
    "price_escalation_unprotected": "No price escalation protection",
    "currency_exposure": "Currency exposure",
    "tax_exposure": "Tax exposure",
    "set_off_rights_one_sided": "One-sided set-off rights",
    "cost_recovery_gap": "Cost recovery gap",
    # Schedule
    "liquidated_damages_exposure": "Liquidated damages exposure",
    "delay_risk": "Delay risk",
    "extension_of_time_restricted": "Restricted extension of time",
    "force_majeure_narrow": "Narrow force majeure relief",
    "milestone_commitment_risk": "Hard milestone commitment",
    # Termination / suspension
    "termination_for_convenience_exposure": "Termination for convenience exposure",
    "termination_notice_short": "Short termination notice",
    "termination_payment_unclear": "Unclear payment on termination",
    "suspension_exposure": "Suspension exposure",
    # Performance
    "performance_guarantee_exposure": "Performance guarantee exposure",
    "warranty_period_onerous": "Onerous warranty period",
    "defects_liability_exposure": "Defects liability exposure",
    "acceptance_criteria_unclear": "Unclear acceptance criteria",
    "kpi_penalty_exposure": "KPI penalty exposure",
    # Insurance
    "insurance_coverage_gap": "Insurance coverage gap",
    "insurance_limits_low": "Insurance limits may be inadequate",
    "deductible_exposure": "Deductible exposure",
    # Compliance
    "hse_obligation_exposure": "HSE obligation exposure",
    "regulatory_compliance_burden": "Regulatory compliance burden",
    "sanctions_exposure": "Sanctions exposure",
    "local_content_obligation": "Local content obligation",
    # Contractual / legal
    "governing_law_unfavourable": "Unfavourable governing law",
    "dispute_resolution_unfavourable": "Unfavourable dispute resolution",
    "confidentiality_obligation": "Confidentiality obligation",
    "ip_rights_transfer": "IP rights transfer",
    "assignment_restriction": "Assignment restriction",
    "subcontracting_restriction": "Subcontracting restriction",
    # Operational
    "client_dependency_risk": "Client dependency risk",
    "weather_risk_unallocated": "Unallocated weather risk",
    "site_conditions_risk": "Site conditions risk",
    "standby_rate_gap": "Standby rate gap",
    "backcharge_exposure": "Backcharge exposure",
    "mobilization_cost_risk": "Mobilization cost risk",
    # Cross-cutting
    "scope_ambiguity": "Scope ambiguity",
    "unbalanced_risk_allocation": "Unbalanced risk allocation",
    # Extended coverage: construction/EPC, supply, IT/SaaS, framework terms
    "variation_claim_time_bar": "Time bar on variation claims",
    "unilateral_variation": "Unilateral variation right",
    "pay_when_paid": "Pay-when-paid / pay-if-paid",
    "late_payment_interest_absent": "No interest on late payment",
    "invoice_rejection_risk": "Strict invoicing conditions",
    "audit_exposure": "Broad audit rights",
    "fitness_for_purpose": "Fitness-for-purpose obligation",
    "design_responsibility": "Design responsibility transferred",
    "latent_conditions_risk": "Unforeseen conditions risk",
    "sla_credit_exposure": "Service credit / SLA exposure",
    "title_risk_transfer": "Title and risk transfer exposure",
    "delivery_obligation_strict": "Strict delivery obligation",
    "exclusive_remedy_limitation": "Exclusive remedy limitation",
    "limitation_period_extended": "Extended limitation period",
    "environmental_liability": "Environmental liability",
    "step_in_rights": "Client step-in rights",
    "auto_renewal": "Automatic renewal",
    "data_protection_exposure": "Data protection obligation",
    "cyber_security_obligation": "Cyber security obligation",
    "export_control_exposure": "Export control exposure",
    "order_of_precedence_risk": "Order of precedence risk",
    "entire_agreement_exclusion": "Entire agreement excludes prior commitments",
    "strict_notice_requirement": "Strict notice requirement",
    "change_of_control_trigger": "Change of control trigger",
    "exclusivity_restriction": "Exclusivity restriction",
    "non_solicitation_restriction": "Non-solicitation restriction",
    "unilateral_amendment": "Unilateral amendment right",
    "sole_discretion": "Discretion reserved to one party",
    "back_to_back_gap": "Back-to-back gap with subcontract",
    "missing_protection": "Missing contractual protection",
    "other": "Other contractual risk",
}

RISK_TYPE_KEYS: list[str] = list(RISK_TYPES)

# Deterministic fallback when the model returns something outside the
# taxonomy: the clause's own subcategory is a far better guess than
# "other", and it's explainable to a reviewer.
_FALLBACK_BY_SUBCATEGORY: dict[str, str] = {
    "payment": "payment_terms_unfavourable",
    "retention": "retention_exposure",
    "advance_payment": "payment_security_gap",
    "price_adjustment": "price_escalation_unprotected",
    "currency": "currency_exposure",
    "tax": "tax_exposure",
    "set_off": "set_off_rights_one_sided",
    "reimbursement": "cost_recovery_gap",
    "milestones": "milestone_commitment_risk",
    "delay": "delay_risk",
    "liquidated_damages": "liquidated_damages_exposure",
    "extension_of_time": "extension_of_time_restricted",
    "force_majeure": "force_majeure_narrow",
    "liability_cap": "liability_cap_low",
    "unlimited_liability": "uncapped_liability",
    "indemnity": "broad_indemnity",
    "consequential_loss": "consequential_loss_exposure",
    "third_party_claims": "third_party_claim_exposure",
    "kpis": "kpi_penalty_exposure",
    "performance_guarantees": "performance_guarantee_exposure",
    "acceptance": "acceptance_criteria_unclear",
    "warranty": "warranty_period_onerous",
    "defects": "defects_liability_exposure",
    "rework": "defects_liability_exposure",
    "termination_for_convenience": "termination_for_convenience_exposure",
    "termination_for_cause": "termination_notice_short",
    "suspension": "suspension_exposure",
    "demobilization": "mobilization_cost_risk",
    "insurance_policy_requirements": "insurance_coverage_gap",
    "insurance_limits": "insurance_limits_low",
    "insurance_deductibles": "deductible_exposure",
    "additional_insured": "insurance_coverage_gap",
    "hse": "hse_obligation_exposure",
    "regulatory": "regulatory_compliance_burden",
    "sanctions": "sanctions_exposure",
    "anti_bribery": "regulatory_compliance_burden",
    "local_content": "local_content_obligation",
    "labor": "regulatory_compliance_burden",
    "governing_law": "governing_law_unfavourable",
    "jurisdiction": "dispute_resolution_unfavourable",
    "arbitration": "dispute_resolution_unfavourable",
    "confidentiality": "confidentiality_obligation",
    "ip": "ip_rights_transfer",
    "assignment": "assignment_restriction",
    "subcontracting": "subcontracting_restriction",
    "mobilization": "mobilization_cost_risk",
    "equipment": "cost_recovery_gap",
    "personnel": "cost_recovery_gap",
    "standby": "standby_rate_gap",
    "weather": "weather_risk_unallocated",
    "site_conditions": "site_conditions_risk",
    "client_dependencies": "client_dependency_risk",
    "npt": "standby_rate_gap",
    "backcharges": "backcharge_exposure",
    "invoicing": "invoice_rejection_risk",
    "variations": "unilateral_variation",
    "payment_security": "payment_security_gap",
    "audit_rights": "audit_exposure",
    "pay_when_paid": "pay_when_paid",
    "delivery": "delivery_obligation_strict",
    "suspension_of_works": "suspension_exposure",
    "exclusive_remedies": "exclusive_remedy_limitation",
    "limitation_period": "limitation_period_extended",
    "environmental_liability": "environmental_liability",
    "fitness_for_purpose": "fitness_for_purpose",
    "design_responsibility": "design_responsibility",
    "service_levels": "sla_credit_exposure",
    "title_and_risk": "title_risk_transfer",
    "step_in": "step_in_rights",
    "term_and_renewal": "auto_renewal",
    "data_protection": "data_protection_exposure",
    "cyber_security": "cyber_security_obligation",
    "export_control": "export_control_exposure",
    "scope_of_work": "scope_ambiguity",
    "order_of_precedence": "order_of_precedence_risk",
    "entire_agreement": "entire_agreement_exclusion",
    "notices": "strict_notice_requirement",
    "change_of_control": "change_of_control_trigger",
    "exclusivity": "exclusivity_restriction",
    "non_solicitation": "non_solicitation_restriction",
    "amendment": "unilateral_amendment",
}


def normalize_risk_type(raw: str | None, *, subcategory: str | None) -> str:
    """Map whatever the provider returned onto the taxonomy.

    Accepts an exact key, a display label, or a loosely-formatted variant
    ("Uncapped Liability", "uncapped-liability"). Anything else falls back
    to the clause's subcategory mapping, then to "other".
    """
    if raw:
        candidate = raw.strip().lower().replace(" ", "_").replace("-", "_")
        if candidate in RISK_TYPES:
            return candidate
        for key, label in RISK_TYPES.items():
            if candidate == label.lower().replace(" ", "_").replace("-", "_"):
                return key

    if subcategory and subcategory in _FALLBACK_BY_SUBCATEGORY:
        return _FALLBACK_BY_SUBCATEGORY[subcategory]
    return "other"


def risk_type_label(key: str) -> str:
    return RISK_TYPES.get(key, RISK_TYPES["other"])
