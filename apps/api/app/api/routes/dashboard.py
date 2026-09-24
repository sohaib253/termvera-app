from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.dashboard import DashboardSummaryRead
from app.services import dashboard as dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/summary", response_model=DashboardSummaryRead)
async def get_dashboard_summary(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryRead:
    summary = await dashboard_service.get_dashboard_summary(
        db, organization_id=principal.organization.id
    )
    return DashboardSummaryRead.model_validate(summary)
