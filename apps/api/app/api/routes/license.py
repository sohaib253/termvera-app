from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal, require_admin
from app.db.session import get_db
from app.schemas.license import LicensePlanUpdate, LicenseRead, UsageRead
from app.services import license as license_service

router = APIRouter(prefix="/api", tags=["license"])


@router.get("/license", response_model=LicenseRead)
async def get_license(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    license_account = await license_service.get_or_create_license(
        db, organization_id=principal.organization.id
    )
    return LicenseRead.model_validate(license_account)


@router.patch("/license", response_model=LicenseRead)
async def update_license_plan(
    data: LicensePlanUpdate,
    principal: CurrentPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    """Workspace administrators set their own plan here. There's no payment
    provider to buy one from (see docs/licensing.md), so this is a direct
    entitlement control, gated on the membership role rather than pretending
    to be a purchase flow."""
    license_account = await license_service.set_plan(
        db,
        organization_id=principal.organization.id,
        plan=data.plan,
        enabled_modules=data.enabled_modules,
    )
    return LicenseRead.model_validate(license_account)


@router.get("/usage", response_model=UsageRead)
async def get_usage(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> UsageRead:
    summary = await license_service.get_usage_summary(db, organization_id=principal.organization.id)
    return UsageRead(
        license=LicenseRead.model_validate(summary["license"]),
        projects_used=summary["projects_used"],
        documents_used_this_period=summary["documents_used_this_period"],
        analyses_used_this_period=summary["analyses_used_this_period"],
        contracts_used=summary["contracts_used"],
        clause_analyses_used_this_period=summary["clause_analyses_used_this_period"],
        period_start=summary["period_start"],
    )
