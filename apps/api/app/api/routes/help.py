"""What the analysis engine checks, for the in-app Help page.

Generated from the engine's own knowledge bases (app/services/brain), not
written separately, so the published checklist is always exactly what the
software applies. Adding a rule to the engine adds it here. Public: it
describes the product, not anyone's data, and a website can reuse it.
"""

import re
from collections import defaultdict

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.brain import tender_kb
from app.services.brain.contract_kb import PROTECTIONS, RULES
from app.services.clauserisk.risk_categories import CATEGORIES as CLAUSE_CATEGORIES
from app.services.clauserisk.risk_types import risk_type_label

router = APIRouter(prefix="/api/help", tags=["help"])

# Rule id prefix -> the risk area it belongs to.
_RULE_AREAS = {
    "LIA": "Liability & indemnity",
    "COM": "Commercial & payment",
    "SCH": "Schedule & delay",
    "PER": "Performance & warranty",
    "TER": "Termination & suspension",
    "INS": "Insurance",
    "CON": "Contractual & legal",
    "CMP": "Compliance & regulatory",
    "OPS": "Operational",
    "GEN": "General",
}
_PROTECTION_AREAS = {
    "liability": "Liability & indemnity",
    "commercial": "Commercial & payment",
    "schedule": "Schedule & delay",
    "performance": "Performance & warranty",
    "termination": "Termination & suspension",
    "insurance": "Insurance",
    "contractual": "Contractual & legal",
    "compliance": "Compliance & regulatory",
}
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}

# Plain-English summary of each tender area, keyed by the engine's category
# name. The engine's own cues are word stems and patterns ("mobili[sz]"),
# fine for matching but not for a customer to read. An area the engine
# gains without an entry here falls back to its cleaned-up cues.
_TENDER_AREA_SUMMARY = {
    "Mandatory Forms": "Forms of tender, bid submission letters, declarations and returnable schedules.",
    "Tender Administration": (
        "Submission deadline and method, bid validity, bid bond or security, clarifications, site"
        " visits and pre-bid meetings."
    ),
    "Certification & Compliance": (
        "ISO and other certificates, accreditations, licences, registrations and permits."
    ),
    "HSE": (
        "HSE management system, safety statistics (TRIR, LTIF), incident reporting and emergency "
        "response."
    ),
    "Experience & Track Record": "Similar projects completed, references and past performance.",
    "Financial Standing": (
        "Turnover, audited financial statements, net worth, liquidity, credit rating and bank "
        "references."
    ),
    "Insurance & Liability": (
        "Insurance cover and levels, indemnities and the liability position the bid accepts."
    ),
    "Local Content": (
        "In-country value (ICV), local content, nationalisation and use of local suppliers and "
        "workforce."
    ),
    "Commercial": (
        "Pricing basis, day rates and lump sums, payment and invoicing terms, currency, discounts"
        " and escalation."
    ),
    "Personnel & Resources": "Key personnel, supervisors and crews, CVs and qualifications.",
    "Quality": "Quality management system, QA/QC, and inspection and test plans.",
    "Technical": "Equipment and capacity, specifications and ratings, methods, mobilisation and calibration.",
    "Legal & Ethics": (
        "Conflict of interest, anti-bribery and corruption, sanctions, ethics and acceptance of "
        "terms."
    ),
    "Evaluation": "Evaluation method, scoring, weightings and award criteria.",
}


class ContractCheck(BaseModel):
    id: str
    title: str
    severity: str
    why_it_matters: str
    what_to_negotiate: str


class ContractArea(BaseModel):
    area: str
    checks: list[ContractCheck]


class MissingProtection(BaseModel):
    title: str
    area: str
    severity: str
    why_it_matters: str
    what_to_negotiate: str


class ClauseFamily(BaseModel):
    family: str
    clause_types: list[str]


class TenderArea(BaseModel):
    area: str
    summary: str


class HelpChecklists(BaseModel):
    contract_rule_count: int
    contract_areas: list[ContractArea]
    missing_protections: list[MissingProtection]
    clause_families: list[ClauseFamily]
    tender_areas: list[TenderArea]
    tender_evidence_anchors: list[str]


def _humanise(key: str) -> str:
    return key.replace("_", " ").capitalize()


def _cue(pattern: str) -> str:
    """A readable rendering of a matching pattern, for "looks for" lists."""
    text = re.sub(r"\[(.)[^\]]*\]", r"\1", pattern)  # "mobili[sz]" -> "mobilis"
    text = text.replace("\\b", "").replace("(?:", "(").replace("\\s+", " ")
    for token in ("?", "\\", "^", "$"):
        text = text.replace(token, "")
    return text.replace("(", "").replace(")", "").replace("|", " / ").strip()


@router.get("/checklists", response_model=HelpChecklists)
async def checklists() -> HelpChecklists:
    by_area: dict[str, list[ContractCheck]] = defaultdict(list)
    for rule in RULES:
        by_area[_RULE_AREAS.get(rule.id.split("-")[0], "General")].append(
            ContractCheck(
                id=rule.id,
                title=risk_type_label(rule.risk_type),
                severity=rule.severity,
                why_it_matters=rule.description,
                what_to_negotiate=rule.action,
            )
        )
    contract_areas = [
        ContractArea(
            area=area,
            checks=sorted(checks, key=lambda c: (_SEVERITY_ORDER.get(c.severity, 9), c.id)),
        )
        for area, checks in sorted(by_area.items(), key=lambda item: -len(item[1]))
    ]

    missing = [
        MissingProtection(
            title=risk_type_label(p.risk_type),
            area=_PROTECTION_AREAS.get(p.category, _humanise(p.category)),
            severity=p.severity,
            why_it_matters=p.description,
            what_to_negotiate=p.action,
        )
        for p in sorted(PROTECTIONS, key=lambda p: _SEVERITY_ORDER.get(p.severity, 9))
    ]

    return HelpChecklists(
        contract_rule_count=len(RULES),
        contract_areas=contract_areas,
        missing_protections=missing,
        clause_families=[
            ClauseFamily(family=_humanise(family), clause_types=[_humanise(t) for t in types])
            for family, types in CLAUSE_CATEGORIES.items()
        ],
        tender_areas=[
            TenderArea(
                area=name,
                summary=_TENDER_AREA_SUMMARY.get(name)
                or ", ".join(_cue(p) for p in patterns).capitalize() + ".",
            )
            for name, patterns in tender_kb.CATEGORIES
        ],
        tender_evidence_anchors=list(tender_kb.ANCHORS),
    )
