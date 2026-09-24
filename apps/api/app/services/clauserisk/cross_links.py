"""Deterministic (non-AI) cross-clause link building — pipeline stage 9.

Two independent, fully deterministic sources of links:

1. Explicit textual references ("as defined in Clause 12.3", "subject to
   Section 5") found by regex in the clause's own text.
2. Configured category-pair patterns (app/services/clauserisk/
   risk_categories.py CATEGORY_PAIR_LINKS) — e.g. every liquidated_damages
   clause is linked to every milestones clause in the same contract
   version, because the brief is explicit that "the LD clause cannot be
   interpreted independently of the completion date clause."

Neither source touches the AI. Links are then used to hand richer context
to the risk-analysis AI call for a clause (see
app/services/clauserisk/pipeline.py), and are shown in the UI so a
reviewer can see *why* two clauses were considered together.
"""

import re
from dataclasses import dataclass

from app.services.clauserisk.risk_categories import CATEGORY_PAIR_LINKS

_REFERENCE_RE = re.compile(
    r"(?:clause|section|article)\s+(\d{1,3}(?:\.\d{1,3}){0,4})", re.IGNORECASE
)


@dataclass
class ClauseForLinking:
    id: str
    clause_number: str | None
    text: str
    subcategory: str | None


@dataclass
class LinkResult:
    clause_a_id: str
    clause_b_id: str
    relationship_type: str
    basis: str  # "explicit_reference" | "category_pattern"


def build_cross_clause_links(clauses: list[ClauseForLinking]) -> list[LinkResult]:
    by_number = {c.clause_number: c for c in clauses if c.clause_number}
    seen: set[tuple[str, str, str]] = set()
    links: list[LinkResult] = []

    for clause in clauses:
        for match in _REFERENCE_RE.finditer(clause.text):
            referenced_number = match.group(1)
            if referenced_number == clause.clause_number:
                continue
            target = by_number.get(referenced_number)
            if target is None:
                continue
            key = _canonical_key(clause.id, target.id, "explicit_reference")
            if key in seen:
                continue
            seen.add(key)
            links.append(
                LinkResult(
                    clause_a_id=clause.id,
                    clause_b_id=target.id,
                    relationship_type="explicit_reference",
                    basis="explicit_reference",
                )
            )

    for i, clause_a in enumerate(clauses):
        if not clause_a.subcategory:
            continue
        for clause_b in clauses[i + 1 :]:
            if not clause_b.subcategory:
                continue
            relationship_type = _matching_relationship(clause_a.subcategory, clause_b.subcategory)
            if relationship_type is None:
                continue
            key = _canonical_key(clause_a.id, clause_b.id, relationship_type)
            if key in seen:
                continue
            seen.add(key)
            links.append(
                LinkResult(
                    clause_a_id=clause_a.id,
                    clause_b_id=clause_b.id,
                    relationship_type=relationship_type,
                    basis="category_pattern",
                )
            )

    return links


def _matching_relationship(subcategory_a: str, subcategory_b: str) -> str | None:
    for sub_x, sub_y, relationship_type in CATEGORY_PAIR_LINKS:
        if {subcategory_a, subcategory_b} == {sub_x, sub_y}:
            return relationship_type
    return None


def _canonical_key(id_a: str, id_b: str, relationship_type: str) -> tuple[str, str, str]:
    ordered = tuple(sorted([id_a, id_b]))
    return (ordered[0], ordered[1], relationship_type)
