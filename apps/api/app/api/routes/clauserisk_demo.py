from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.contract import ContractDetailRead
from app.services.clauserisk import demo as demo_service

router = APIRouter(prefix="/api/clauserisk/demo", tags=["clauserisk-demo"])


@router.post("/load", response_model=ContractDetailRead, status_code=status.HTTP_201_CREATED)
async def load_demo_contract(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractDetailRead:
    try:
        contract = await demo_service.create_demo_contract(
            db, organization_id=principal.organization.id, created_by_user_id=principal.user.id
        )
    except demo_service.SampleDataMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return ContractDetailRead.model_validate(contract)
