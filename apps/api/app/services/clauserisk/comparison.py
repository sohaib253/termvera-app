"""Contract version comparison — fully deterministic, no AI call.

Clauses are matched between versions by clause_number. This is
intentionally simple: a clause renumbered between versions will show up
as one "deleted" and one "added" rather than a "modified" match. Matching
by similarity/content instead of number is a reasonable future
improvement, not attempted here (see docs/architecture.md).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clause import Clause
from app.models.contract_comparison import ContractChange, ContractComparison
from app.services.clauserisk.access import ClauseRiskNotFoundError, get_owned_version

_MATERIAL_CATEGORIES = {"commercial", "liability", "schedule", "termination", "insurance"}


async def compare_versions(
    db: AsyncSession,
    *,
    organization_id: str,
    contract_id: str,
    base_version_id: str,
    compared_version_id: str,
    created_by_user_id: str,
) -> ContractComparison:
    base_version = await get_owned_version(
        db, organization_id=organization_id, contract_version_id=base_version_id
    )
    compared_version = await get_owned_version(
        db, organization_id=organization_id, contract_version_id=compared_version_id
    )
    if base_version.contract_id != contract_id or compared_version.contract_id != contract_id:
        raise ClauseRiskNotFoundError("Both versions must belong to the specified contract.")

    base_clauses = {
        c.clause_number: c
        for c in await db.scalars(select(Clause).where(Clause.contract_version_id == base_version_id))
        if c.clause_number
    }
    compared_clauses = {
        c.clause_number: c
        for c in await db.scalars(
            select(Clause).where(Clause.contract_version_id == compared_version_id)
        )
        if c.clause_number
    }

    comparison = ContractComparison(
        contract_id=contract_id,
        base_version_id=base_version_id,
        compared_version_id=compared_version_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(comparison)
    await db.flush()

    for number, compared_clause in compared_clauses.items():
        base_clause = base_clauses.get(number)
        if base_clause is None:
            db.add(
                ContractChange(
                    comparison_id=comparison.id,
                    change_type="added",
                    clause_number=number,
                    category=compared_clause.category,
                    compared_clause_id=compared_clause.id,
                    description=f"Clause {number} ({compared_clause.title}) is new in this version.",
                    materiality=_materiality_for_category(compared_clause.category),
                )
            )
            continue

        change = _diff_clause(base_clause, compared_clause)
        if change is not None:
            db.add(
                ContractChange(
                    comparison_id=comparison.id,
                    change_type="modified",
                    clause_number=number,
                    category=compared_clause.category,
                    base_clause_id=base_clause.id,
                    compared_clause_id=compared_clause.id,
                    description=change["description"],
                    materiality=change["materiality"],
                    financial_delta=change.get("financial_delta"),
                )
            )

    for number, base_clause in base_clauses.items():
        if number not in compared_clauses:
            db.add(
                ContractChange(
                    comparison_id=comparison.id,
                    change_type="deleted",
                    clause_number=number,
                    category=base_clause.category,
                    base_clause_id=base_clause.id,
                    description=f"Clause {number} ({base_clause.title}) was removed in this version.",
                    materiality=_materiality_for_category(base_clause.category),
                )
            )

    await db.commit()
    await db.refresh(comparison, attribute_names=["changes"])
    return comparison


def _materiality_for_category(category: str | None) -> str:
    return "material" if category in _MATERIAL_CATEGORIES else "minor"


def _diff_clause(base: Clause, compared: Clause) -> dict | None:
    changes: list[str] = []
    financial_delta: str | None = None

    if base.category != compared.category:
        changes.append(f"category changed from '{base.category}' to '{compared.category}'")

    base_amounts = set(base.get_list_field("extracted_amounts"))
    compared_amounts = set(compared.get_list_field("extracted_amounts"))
    if base_amounts != compared_amounts:
        changes.append(f"amounts changed from {sorted(base_amounts)} to {sorted(compared_amounts)}")
        financial_delta = f"{sorted(base_amounts)} -> {sorted(compared_amounts)}"

    base_percentages = set(base.get_list_field("extracted_percentages"))
    compared_percentages = set(compared.get_list_field("extracted_percentages"))
    if base_percentages != compared_percentages:
        changes.append(
            f"percentages changed from {sorted(base_percentages)} to {sorted(compared_percentages)}"
        )

    base_dates = set(base.get_list_field("extracted_dates"))
    compared_dates = set(compared.get_list_field("extracted_dates"))
    if base_dates != compared_dates:
        changes.append(f"dates changed from {sorted(base_dates)} to {sorted(compared_dates)}")

    # Payment days, notice periods, and warranty durations are often the
    # most consequential edit in an amendment ("30 days" -> "7 days").
    base_periods = set(base.get_list_field("extracted_time_periods"))
    compared_periods = set(compared.get_list_field("extracted_time_periods"))
    if base_periods != compared_periods:
        changes.append(f"time periods changed from {sorted(base_periods)} to {sorted(compared_periods)}")

    base_obligations = set(base.get_list_field("extracted_obligations"))
    compared_obligations = set(compared.get_list_field("extracted_obligations"))
    if base_obligations != compared_obligations:
        changes.append("obligations text changed")

    if base.text.strip() != compared.text.strip() and not changes:
        changes.append("clause text changed")

    if not changes:
        return None

    category = compared.category or base.category
    numeric_fields_changed = (
        base_amounts != compared_amounts
        or base_percentages != compared_percentages
        or base_dates != compared_dates
        or base_periods != compared_periods
    )
    materiality = "material" if numeric_fields_changed else _materiality_for_category(category)

    return {
        "description": f"Clause {compared.clause_number}: " + "; ".join(changes) + ".",
        "materiality": materiality,
        "financial_delta": financial_delta,
    }
