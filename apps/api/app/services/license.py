"""Local development / demo entitlement fixture — see docs/licensing.md.

This is NOT a production license enforcement system: there is no signed
token, no remote validation, and no payment integration. Every
organization gets a demo-plan LicenseAccount row on first access, with
generous-but-real limits that are actually enforced (project count,
monthly document uploads, monthly analysis runs, contract count, monthly
clause-analysis runs) so the plumbing for real entitlements is genuine,
even though the plan itself is a fixture.

Module entitlements (TenderGuard / ClauseRisk / both) are similarly real
but not cryptographically enforced — see check_module_entitlement.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract
from app.models.license import LicenseAccount, LicenseModule, LicensePlan, UsageEvent
from app.models.project import Project


class UsageLimitExceededError(Exception):
    pass


class ModuleNotEntitledError(Exception):
    pass


# A limit of -1 means "no ceiling". Stored as a sentinel rather than a
# nullable column so every limit stays a plain int at the call sites, and
# so an unlimited plan is visible in the same field the UI already shows.
UNLIMITED = -1


def is_unlimited(limit: int) -> bool:
    return limit < 0


async def get_or_create_license(db: AsyncSession, *, organization_id: str) -> LicenseAccount:
    license_account = await db.scalar(
        select(LicenseAccount).where(LicenseAccount.organization_id == organization_id)
    )
    if license_account is None:
        license_account = LicenseAccount(organization_id=organization_id)
        db.add(license_account)
        await db.commit()
        await db.refresh(license_account)
    return license_account


def _current_period_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _usage_count(db: AsyncSession, *, organization_id: str, event_type: str) -> int:
    period_start = _current_period_start()
    result = await db.scalar(
        select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.event_type == event_type,
            UsageEvent.created_at >= period_start,
        )
    )
    return int(result or 0)


async def check_module_entitlement(
    db: AsyncSession, *, organization_id: str, module: LicenseModule
) -> None:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    if not license_account.has_module(module):
        raise ModuleNotEntitledError(
            f"This workspace's plan does not include the {module.value} module. "
            "Contact us to add it."
        )


async def check_project_limit(db: AsyncSession, *, organization_id: str) -> None:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    if is_unlimited(license_account.project_limit):
        return
    count = await db.scalar(
        select(func.count()).select_from(Project).where(
            Project.organization_id == organization_id, Project.deleted_at.is_(None)
        )
    )
    if (count or 0) >= license_account.project_limit:
        raise UsageLimitExceededError(
            f"This workspace's plan allows up to {license_account.project_limit} projects. "
            "Contact us to discuss a higher limit."
        )


async def check_contract_limit(db: AsyncSession, *, organization_id: str) -> None:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    if is_unlimited(license_account.monthly_contract_limit):
        return
    # Contracts belong to projects, which belong to the org, so join through.
    count = await db.scalar(
        select(func.count())
        .select_from(Contract)
        .join(Project, Project.id == Contract.project_id)
        .where(Project.organization_id == organization_id, Contract.deleted_at.is_(None))
    )
    if (count or 0) >= license_account.monthly_contract_limit:
        raise UsageLimitExceededError(
            f"This workspace's plan allows up to {license_account.monthly_contract_limit} "
            "contracts. Contact us to discuss a higher limit."
        )


async def check_and_report_usage(
    db: AsyncSession, *, organization_id: str, event_type: str, limit_field: str
) -> None:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    limit = getattr(license_account, limit_field)
    if not is_unlimited(limit):
        current = await _usage_count(db, organization_id=organization_id, event_type=event_type)
        if current >= limit:
            raise UsageLimitExceededError(
                f"This workspace's plan allows {limit} {event_type.replace('_', ' ')} per month. "
                "Contact us to discuss a higher limit."
            )
    # Usage is still recorded on unlimited plans: the numbers are what a
    # future paid tier would bill on, and what the workspace owner sees.
    db.add(UsageEvent(organization_id=organization_id, event_type=event_type, quantity=1))


# Plan presets. Without a payment provider there is nothing to "buy", so a
# workspace admin selects a plan directly (see docs/licensing.md for what a
# real entitlement system would add). Enterprise is unlimited so an admin
# can work without hitting fixture limits.
PLAN_PRESETS: dict[LicensePlan, dict[str, int]] = {
    LicensePlan.DEMO: {
        "seat_limit": 3,
        "project_limit": 3,
        "monthly_document_limit": 20,
        "monthly_analysis_limit": 10,
        "monthly_contract_limit": 10,
        "monthly_clause_analysis_limit": 10,
    },
    LicensePlan.TRIAL: {
        "seat_limit": 5,
        "project_limit": 10,
        "monthly_document_limit": 50,
        "monthly_analysis_limit": 25,
        "monthly_contract_limit": 25,
        "monthly_clause_analysis_limit": 25,
    },
    LicensePlan.PROFESSIONAL: {
        "seat_limit": 25,
        "project_limit": 100,
        "monthly_document_limit": 500,
        "monthly_analysis_limit": 250,
        "monthly_contract_limit": 250,
        "monthly_clause_analysis_limit": 250,
    },
    LicensePlan.ENTERPRISE: {
        "seat_limit": UNLIMITED,
        "project_limit": UNLIMITED,
        "monthly_document_limit": UNLIMITED,
        "monthly_analysis_limit": UNLIMITED,
        "monthly_contract_limit": UNLIMITED,
        "monthly_clause_analysis_limit": UNLIMITED,
    },
}


async def set_plan(
    db: AsyncSession,
    *,
    organization_id: str,
    plan: LicensePlan,
    enabled_modules: list[str] | None = None,
) -> LicenseAccount:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    license_account.plan = plan
    for field, value in PLAN_PRESETS[plan].items():
        setattr(license_account, field, value)
    if enabled_modules is not None:
        license_account.enabled_modules = json.dumps(enabled_modules)
    await db.commit()
    await db.refresh(license_account)
    return license_account


async def get_usage_summary(db: AsyncSession, *, organization_id: str) -> dict:
    license_account = await get_or_create_license(db, organization_id=organization_id)
    project_count = await db.scalar(
        select(func.count()).select_from(Project).where(
            Project.organization_id == organization_id, Project.deleted_at.is_(None)
        )
    )
    contract_count = await db.scalar(
        select(func.count())
        .select_from(Contract)
        .join(Project, Project.id == Contract.project_id)
        .where(Project.organization_id == organization_id, Contract.deleted_at.is_(None))
    )
    documents_this_period = await _usage_count(
        db, organization_id=organization_id, event_type="document_uploaded"
    )
    analyses_this_period = await _usage_count(
        db, organization_id=organization_id, event_type="analysis_run"
    )
    clause_analyses_this_period = await _usage_count(
        db, organization_id=organization_id, event_type="clause_analysis_run"
    )
    return {
        "license": license_account,
        "projects_used": project_count or 0,
        "documents_used_this_period": documents_this_period,
        "analyses_used_this_period": analyses_this_period,
        "contracts_used": contract_count or 0,
        "clause_analyses_used_this_period": clause_analyses_this_period,
        "period_start": _current_period_start(),
    }
