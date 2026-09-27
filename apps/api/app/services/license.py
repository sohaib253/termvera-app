"""Workspace entitlements: trial, license keys, limits. See docs/licensing.md.

Commercial model:
- A new workspace gets a TRIAL_DAYS free trial with every feature.
- Buying a subscription gets a signed license key (license_keys.py);
  activating it sets the plan, seats, modules and paid-up-until date.
- After the trial, or GRACE_DAYS after a subscription lapses, the workspace
  becomes view-only: everything stays readable and exportable, but nothing
  new can be created, uploaded or analysed. Customers are never locked out
  of their own data, which is what keeps renewals friendly.

Every write path already passes through one of the check_* functions
below, so the view-only gate lives there (_ensure_writable).
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.contract import Contract
from app.models.license import (
    LicenseAccount,
    LicenseModule,
    LicensePlan,
    LicenseStatus,
    UsageEvent,
)
from app.models.project import Project
from app.services import license_keys
from app.services.machine_id import machine_id


class UsageLimitExceededError(Exception):
    pass


class ModuleNotEntitledError(Exception):
    pass


class WorkspaceReadOnlyError(UsageLimitExceededError):
    """Trial ended or subscription lapsed. Subclasses UsageLimitExceededError
    so every route that already turns a limit into 402 handles it too."""


TRIAL_DAYS = 14
GRACE_DAYS = 7
# The clock high-water mark is persisted at most this often, not per request.
_CLOCK_WRITE_INTERVAL = timedelta(hours=1)


@dataclass(frozen=True)
class Entitlement:
    # free | trial | trial_expired | active | grace | expired | other_machine
    state: str
    read_only: bool
    ends_at: datetime | None  # when the trial or paid period ends
    days_left: int | None
    licensed_to: str | None
    license_id: str | None


def _aware(value: datetime | None) -> datetime | None:
    # SQLite hands timezone-aware columns back naive; they were stored as UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _days_left(now: datetime, ends_at: datetime) -> int:
    return max(0, (ends_at - now).days + (1 if (ends_at - now).seconds else 0))


def compute_entitlement(account: LicenseAccount, now: datetime) -> Entitlement:
    expires_at = _aware(account.expires_at)
    if account.license_key and _bound_elsewhere(account.license_key):
        # The workspace (its data folder) was copied from the computer the
        # key was issued for. View-only here until this PC has its own key.
        return Entitlement(
            "other_machine", True, None, None, account.licensee, account.license_id
        )
    if account.license_key and expires_at is not None:
        grace_ends = expires_at + timedelta(days=GRACE_DAYS)
        if now <= expires_at:
            state, ends_at = "active", expires_at
        elif now <= grace_ends:
            state, ends_at = "grace", grace_ends
        else:
            state, ends_at = "expired", grace_ends
        return Entitlement(
            state=state,
            read_only=state == "expired",
            ends_at=ends_at,
            days_left=_days_left(now, ends_at),
            licensed_to=account.licensee,
            license_id=account.license_id,
        )

    if account.plan == LicensePlan.FREE:
        return Entitlement("free", False, None, None, None, None)
    if account.plan in (LicensePlan.PROFESSIONAL, LicensePlan.ENTERPRISE):
        # A plan set without a key: only possible through the development-
        # only plan switch (PATCH /api/license outside production).
        return Entitlement("active", False, None, None, account.licensee, account.license_id)

    started = _aware(account.trial_started_at) or _aware(account.created_at) or now
    ends_at = started + timedelta(days=TRIAL_DAYS)
    if now <= ends_at:
        return Entitlement("trial", False, ends_at, _days_left(now, ends_at), None, None)
    return Entitlement("trial_expired", True, ends_at, 0, None, None)


def _bound_elsewhere(key: str) -> bool:
    try:
        claims = license_keys.verify(key)
    except license_keys.InvalidLicenseKeyError:
        return False
    return bool(claims.machine_id) and claims.machine_id != machine_id()


async def get_entitlement(db: AsyncSession, *, organization_id: str) -> Entitlement:
    account = await get_or_create_license(db, organization_id=organization_id)
    real_now = datetime.now(UTC)
    high_water = _aware(account.clock_high_water)
    if high_water is None or real_now - high_water > _CLOCK_WRITE_INTERVAL:
        account.clock_high_water = real_now
        await db.commit()
    now = max(real_now, high_water) if high_water else real_now
    return compute_entitlement(account, now)


async def _ensure_writable(db: AsyncSession, *, organization_id: str) -> None:
    entitlement = await get_entitlement(db, organization_id=organization_id)
    if not entitlement.read_only:
        return
    if entitlement.state == "other_machine":
        raise WorkspaceReadOnlyError(
            "This workspace's license belongs to another computer. Your work is safe and "
            f"viewable; to keep working here, request a key for this computer ({machine_id()})."
        )
    if entitlement.state == "trial_expired":
        raise WorkspaceReadOnlyError(
            "Your free trial has ended. Your work is safe and still viewable; enter a "
            "license key in Settings to keep creating and analysing."
        )
    raise WorkspaceReadOnlyError(
        "Your subscription has ended. Your work is safe and still viewable; renew and "
        "enter your new license key in Settings to keep creating and analysing."
    )


async def activate_license_key(
    db: AsyncSession, *, organization_id: str, key: str
) -> LicenseAccount:
    claims = license_keys.verify(key)
    if claims.machine_id and claims.machine_id != machine_id():
        raise license_keys.InvalidLicenseKeyError(
            f"This key was issued for a different computer ({claims.machine_id}). This "
            f"computer's Machine ID is {machine_id()}: send it to us for a key for this PC."
        )
    if datetime.now(UTC) > license_keys.end_of_day(claims.expires_at) + timedelta(days=GRACE_DAYS):
        raise license_keys.InvalidLicenseKeyError(
            f"This license key expired on {claims.expires_at:%d %b %Y}. Contact us to renew."
        )
    try:
        plan = LicensePlan(claims.plan)
    except ValueError as exc:
        raise license_keys.InvalidLicenseKeyError(
            "This license key is for a plan this version doesn't recognise. Update the app."
        ) from exc

    account = await get_or_create_license(db, organization_id=organization_id)
    account.plan = plan
    for field, value in PLAN_PRESETS[plan].items():
        setattr(account, field, value)
    account.seat_limit = claims.seats
    account.enabled_modules = json.dumps(claims.modules)
    account.expires_at = license_keys.end_of_day(claims.expires_at)
    account.license_key = license_keys.normalise(key)
    account.license_id = claims.license_id
    account.licensee = claims.licensee
    account.status = LicenseStatus.ACTIVE
    await db.commit()
    await db.refresh(account)
    return account


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
    billing = get_settings().billing_enabled
    now = datetime.now(UTC)
    if license_account is None:
        plan = LicensePlan.TRIAL if billing else LicensePlan.FREE
        license_account = LicenseAccount(
            organization_id=organization_id,
            plan=plan,
            **PLAN_PRESETS[plan],
            trial_started_at=now,
            clock_high_water=now,
        )
        db.add(license_account)
        await db.commit()
        await db.refresh(license_account)
        return license_account

    # Moving between early access and paid plans. Workspaces holding a
    # license key are never touched.
    if not license_account.license_key:
        if not billing and license_account.plan in (LicensePlan.TRIAL, LicensePlan.DEMO):
            _apply_plan(license_account, LicensePlan.FREE)
            await db.commit()
        elif billing and license_account.plan == LicensePlan.FREE:
            # Billing just switched on: early users get the full trial from
            # today, not from when they first installed.
            _apply_plan(license_account, LicensePlan.TRIAL)
            license_account.trial_started_at = now
            await db.commit()
    return license_account


def _apply_plan(account: LicenseAccount, plan: LicensePlan) -> None:
    account.plan = plan
    for field, value in PLAN_PRESETS[plan].items():
        setattr(account, field, value)


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
    await _ensure_writable(db, organization_id=organization_id)
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
    await _ensure_writable(db, organization_id=organization_id)
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
    await _ensure_writable(db, organization_id=organization_id)
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


# Limits per plan. Trial is sized for a real evaluation (a live tender and a
# handful of contracts) rather than crippled; Professional covers a busy
# contracts team; Enterprise is unlimited. A license key sets the plan.
PLAN_PRESETS: dict[LicensePlan, dict[str, int]] = {
    # Early access: no ceilings. Usage is still recorded, so there's real
    # data on how people use it when pricing is decided.
    LicensePlan.FREE: {
        "seat_limit": UNLIMITED,
        "project_limit": UNLIMITED,
        "monthly_document_limit": UNLIMITED,
        "monthly_analysis_limit": UNLIMITED,
        "monthly_contract_limit": UNLIMITED,
        "monthly_clause_analysis_limit": UNLIMITED,
    },
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
