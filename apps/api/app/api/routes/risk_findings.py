from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.models.license import LicenseModule
from app.schemas.risk_finding import (
    FindingReviewActionCreate,
    RiskFindingDetailRead,
    RiskFindingListItem,
    RiskFindingRead,
)
from app.services import license as license_service
from app.services.clauserisk import contracts as contract_service
from app.services.clauserisk import review as review_service
from app.services.clauserisk.access import ClauseRiskNotFoundError, get_owned_version

router = APIRouter(tags=["clauserisk-risk-findings"])


@router.get("/api/risk-findings", response_model=list[RiskFindingListItem])
async def list_all_risk_findings(
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[RiskFindingListItem]:
    """Findings across every contract in the organization — backs the
    top-level Risk Register. list_risk_findings below (scoped to one
    contract version) remains the endpoint the Contract detail page uses."""
    try:
        await license_service.check_module_entitlement(
            db, organization_id=principal.organization.id, module=LicenseModule.CLAUSERISK
        )
    except license_service.ModuleNotEntitledError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    rows = await contract_service.list_risk_findings_for_organization(
        db,
        organization_id=principal.organization.id,
        severity=severity,
        category=category,
        reviewer_status=reviewer_status,
    )
    return [
        RiskFindingListItem(
            **RiskFindingRead.model_validate(finding).model_dump(),
            contract_id=contract_id,
            contract_name=contract_name,
            clause_number=clause_number,
        )
        for finding, contract_id, contract_name, clause_number in rows
    ]


@router.get(
    "/api/contract-versions/{version_id}/risk-findings", response_model=list[RiskFindingRead]
)
async def list_risk_findings(
    version_id: str,
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    clause_id: str | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[RiskFindingRead]:
    try:
        await get_owned_version(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract version not found."
        ) from exc

    findings = await contract_service.list_risk_findings(
        db,
        contract_version_id=version_id,
        severity=severity,
        category=category,
        reviewer_status=reviewer_status,
        clause_id=clause_id,
    )
    return [RiskFindingRead.model_validate(f) for f in findings]


@router.get("/api/risk-findings/{finding_id}", response_model=RiskFindingDetailRead)
async def get_risk_finding(
    finding_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> RiskFindingDetailRead:
    try:
        finding = await contract_service.get_finding_detail(
            db, organization_id=principal.organization.id, finding_id=finding_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Risk finding not found."
        ) from exc
    return RiskFindingDetailRead.model_validate(finding)


@router.post("/api/risk-findings/{finding_id}/review", response_model=RiskFindingDetailRead)
async def review_risk_finding(
    finding_id: str,
    data: FindingReviewActionCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> RiskFindingDetailRead:
    try:
        finding = await review_service.apply_finding_review_action(
            db,
            organization_id=principal.organization.id,
            finding_id=finding_id,
            user_id=principal.user.id,
            data=data,
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Risk finding not found."
        ) from exc
    return RiskFindingDetailRead.model_validate(finding)
