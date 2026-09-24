from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.comparison import CompareVersionsRequest, ContractComparisonRead
from app.services.clauserisk import comparison as comparison_service
from app.services.clauserisk.access import ClauseRiskNotFoundError

router = APIRouter(tags=["clauserisk-comparisons"])


@router.post(
    "/api/contracts/{contract_id}/comparisons",
    response_model=ContractComparisonRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_comparison(
    contract_id: str,
    data: CompareVersionsRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractComparisonRead:
    try:
        comparison = await comparison_service.compare_versions(
            db,
            organization_id=principal.organization.id,
            contract_id=contract_id,
            base_version_id=data.base_version_id,
            compared_version_id=data.compared_version_id,
            created_by_user_id=principal.user.id,
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc) or "Not found."
        ) from exc
    return ContractComparisonRead.model_validate(comparison)
