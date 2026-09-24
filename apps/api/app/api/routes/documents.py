from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.models.document import DocumentPage, DocumentType
from app.schemas.document import DocumentPageRead, DocumentRead
from app.services import document as document_service
from app.services import license as license_service
from app.services import project as project_service
from app.services import storage

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


async def _ensure_project_access(
    db: AsyncSession, *, organization_id: str, project_id: str
) -> None:
    try:
        await project_service.get_project(db, organization_id=organization_id, project_id=project_id)
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found."
        ) from exc


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    await _ensure_project_access(
        db, organization_id=principal.organization.id, project_id=project_id
    )

    try:
        await license_service.check_and_report_usage(
            db,
            organization_id=principal.organization.id,
            event_type="document_uploaded",
            limit_field="monthly_document_limit",
        )
    except license_service.UsageLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc

    content = await file.read()
    try:
        document = await document_service.create_document(
            db,
            organization_id=principal.organization.id,
            project_id=project_id,
            uploaded_by_user_id=principal.user.id,
            document_type=document_type,
            filename=file.filename or "upload.pdf",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
    except document_service.InvalidUploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    background_tasks.add_task(document_service.run_extraction, document.id)
    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    project_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentRead]:
    await _ensure_project_access(
        db, organization_id=principal.organization.id, project_id=project_id
    )
    documents = await document_service.list_documents(db, project_id=project_id)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    project_id: str,
    document_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    await _ensure_project_access(
        db, organization_id=principal.organization.id, project_id=project_id
    )
    try:
        document = await document_service.get_document(
            db, project_id=project_id, document_id=document_id
        )
    except document_service.DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from exc
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/pages", response_model=list[DocumentPageRead])
async def get_document_pages(
    project_id: str,
    document_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentPageRead]:
    await _ensure_project_access(
        db, organization_id=principal.organization.id, project_id=project_id
    )
    try:
        await document_service.get_document(db, project_id=project_id, document_id=document_id)
    except document_service.DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from exc

    pages = await db.scalars(
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    return [DocumentPageRead.model_validate(p) for p in pages]


@router.get("/{document_id}/file")
async def get_document_file(
    project_id: str,
    document_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _ensure_project_access(
        db, organization_id=principal.organization.id, project_id=project_id
    )
    try:
        document = await document_service.get_document(
            db, project_id=project_id, document_id=document_id
        )
    except document_service.DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from exc

    content = storage.read_document_file(document.storage_path)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{document.original_filename}"'},
    )
