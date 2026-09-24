from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.requirement import RequirementDetailRead, RequirementRead, ReviewActionCreate
from app.services import requirement as requirement_service
from app.services.project import ProjectNotFoundError

router = APIRouter(tags=["requirements"])


@router.get("/api/projects/{project_id}/requirements", response_model=list[RequirementRead])
async def list_requirements(
    project_id: str,
    status: str | None = Query(default=None),
    mandatory_status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[RequirementRead]:
    try:
        requirements = await requirement_service.list_requirements(
            db,
            organization_id=principal.organization.id,
            project_id=project_id,
            status=status,
            mandatory_status=mandatory_status,
            priority=priority,
            reviewer_status=reviewer_status,
            search=search,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found."
        ) from exc
    return [RequirementRead.model_validate(r) for r in requirements]


@router.get("/api/requirements/{requirement_id}", response_model=RequirementDetailRead)
async def get_requirement(
    requirement_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> RequirementDetailRead:
    try:
        requirement = await requirement_service.get_requirement_detail(
            db, organization_id=principal.organization.id, requirement_id=requirement_id
        )
    except requirement_service.RequirementNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Requirement not found."
        ) from exc
    return RequirementDetailRead.model_validate(requirement)


@router.post("/api/requirements/{requirement_id}/review", response_model=RequirementDetailRead)
async def review_requirement(
    requirement_id: str,
    data: ReviewActionCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> RequirementDetailRead:
    try:
        requirement = await requirement_service.apply_review_action(
            db,
            organization_id=principal.organization.id,
            requirement_id=requirement_id,
            user_id=principal.user.id,
            data=data,
        )
    except requirement_service.RequirementNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Requirement not found."
        ) from exc
    return RequirementDetailRead.model_validate(requirement)
