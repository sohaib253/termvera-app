from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.project import ProjectRead
from app.services import demo as demo_service

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/load", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def load_demo_project(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    try:
        project = await demo_service.create_demo_project(
            db,
            organization_id=principal.organization.id,
            created_by_user_id=principal.user.id,
        )
    except demo_service.SampleDataMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return ProjectRead.model_validate(project)
