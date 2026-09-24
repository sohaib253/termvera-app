from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.base import utcnow
from app.db.session import get_db
from app.models.project import AnalysisStatus, Project
from app.schemas.analysis import AnalysisStatusRead
from app.services import analysis as analysis_service
from app.services import license as license_service

router = APIRouter(prefix="/api/projects/{project_id}/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisStatusRead, status_code=http_status.HTTP_202_ACCEPTED)
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusRead:
    if analysis_service.get_ai_provider() is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                "AI provider not configured. Set ANTHROPIC_API_KEY on the API server to "
                "enable requirement extraction and compliance assessment, or explore the "
                "sample project instead (see the Demo section)."
            ),
        )

    try:
        await analysis_service.check_analysis_preconditions(
            db, organization_id=principal.organization.id, project_id=project_id
        )
    except analysis_service.AnalysisPreconditionError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        await license_service.check_and_report_usage(
            db,
            organization_id=principal.organization.id,
            event_type="analysis_run",
            limit_field="monthly_analysis_limit",
        )
    except license_service.UsageLimitExceededError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc

    project = await db.get(Project, project_id)
    assert project is not None  # guaranteed by check_analysis_preconditions above
    project.analysis_status = AnalysisStatus.PROCESSING
    project.analysis_error = None
    project.analysis_started_at = utcnow()
    project.analysis_completed_at = None
    await db.commit()

    background_tasks.add_task(analysis_service.run_analysis, project_id)

    return AnalysisStatusRead(
        analysis_status=project.analysis_status,
        analysis_error=project.analysis_error,
        analysis_started_at=project.analysis_started_at,
        analysis_completed_at=project.analysis_completed_at,
    )


@router.get("", response_model=AnalysisStatusRead)
async def get_analysis_status(
    project_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusRead:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != principal.organization.id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return AnalysisStatusRead(
        analysis_status=project.analysis_status,
        analysis_error=project.analysis_error,
        analysis_started_at=project.analysis_started_at,
        analysis_completed_at=project.analysis_completed_at,
    )
