from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.services import export_excel
from app.services import project as project_service

router = APIRouter(prefix="/api/projects/{project_id}/exports", tags=["exports"])


@router.get("/compliance-matrix.xlsx")
async def export_compliance_matrix(
    project_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        project = await project_service.get_project(
            db, organization_id=principal.organization.id, project_id=project_id
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found."
        ) from exc

    content = await export_excel.build_compliance_matrix_workbook(db, project=project)
    filename = f"{project.name.replace(' ', '-')}-compliance-matrix.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
