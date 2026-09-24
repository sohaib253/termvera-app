from fastapi import APIRouter, Depends

from app.api.deps import CurrentPrincipal, get_current_principal
from app.schemas.organization import OrganizationRead
from app.schemas.user import MeResponse, UserRead

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=MeResponse)
async def read_me(principal: CurrentPrincipal = Depends(get_current_principal)) -> MeResponse:
    return MeResponse(
        user=UserRead.model_validate(principal.user),
        organization=OrganizationRead.model_validate(principal.organization),
        role=principal.role,
        is_admin=principal.is_admin,
    )
