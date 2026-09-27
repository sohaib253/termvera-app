from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal, require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.license import LicenseAccount
from app.schemas.license import LicenseActivate, LicensePlanUpdate, LicenseRead, UsageRead
from app.services import license as license_service
from app.services import license_keys
from app.services.machine_id import machine_id

router = APIRouter(prefix="/api", tags=["license"])


def _license_read(account: LicenseAccount, entitlement: license_service.Entitlement) -> LicenseRead:
    read = LicenseRead.model_validate(account)
    bound: str | None = None
    if account.license_key:
        try:
            bound = license_keys.verify(account.license_key).machine_id
        except license_keys.InvalidLicenseKeyError:
            bound = None
    return read.model_copy(
        update={
            "state": entitlement.state,
            "read_only": entitlement.read_only,
            "ends_at": entitlement.ends_at,
            "days_left": entitlement.days_left,
            "licensed_to": entitlement.licensed_to,
            "license_id": entitlement.license_id,
            "machine_id": machine_id(),
            "bound_machine_id": bound,
        }
    )


async def _current(db: AsyncSession, organization_id: str) -> LicenseRead:
    entitlement = await license_service.get_entitlement(db, organization_id=organization_id)
    account = await license_service.get_or_create_license(db, organization_id=organization_id)
    return _license_read(account, entitlement)


@router.get("/license", response_model=LicenseRead)
async def get_license(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    return await _current(db, principal.organization.id)


@router.post("/license/activate", response_model=LicenseRead)
async def activate_license(
    data: LicenseActivate,
    principal: CurrentPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    """Apply a signed license key (see app/services/license_keys.py). The key
    is verified offline against the embedded public key."""
    try:
        await license_service.activate_license_key(
            db, organization_id=principal.organization.id, key=data.key
        )
    except license_keys.InvalidLicenseKeyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return await _current(db, principal.organization.id)


@router.patch("/license", response_model=LicenseRead)
async def update_license_plan(
    data: LicensePlanUpdate,
    principal: CurrentPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    """Development and testing only. In a customer install the plan comes
    from a license key; letting a workspace admin pick "enterprise" here
    would give the product away."""
    if get_settings().environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plans are set by activating a license key.",
        )
    await license_service.set_plan(
        db,
        organization_id=principal.organization.id,
        plan=data.plan,
        enabled_modules=data.enabled_modules,
    )
    return await _current(db, principal.organization.id)


@router.get("/usage", response_model=UsageRead)
async def get_usage(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> UsageRead:
    summary = await license_service.get_usage_summary(db, organization_id=principal.organization.id)
    return UsageRead(
        license=await _current(db, principal.organization.id),
        projects_used=summary["projects_used"],
        documents_used_this_period=summary["documents_used_this_period"],
        analyses_used_this_period=summary["analyses_used_this_period"],
        contracts_used=summary["contracts_used"],
        clause_analyses_used_this_period=summary["clause_analyses_used_this_period"],
        period_start=summary["period_start"],
    )
