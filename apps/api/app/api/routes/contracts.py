from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.api.routes.documents import document_file_response
from app.db.base import utcnow
from app.db.session import get_db
from app.models.contract import ContractAnalysisStatus
from app.models.license import LicenseModule
from app.schemas.analysis import ContractAnalysisStatusRead
from app.schemas.clause import ClauseDetailRead, ClauseRead, CrossClauseLinkRead
from app.schemas.contract import (
    ContractCreate,
    ContractDetailRead,
    ContractListItem,
    ContractRead,
    ContractUpdate,
    ContractVersionRead,
)
from app.services import document as document_service
from app.services import license as license_service
from app.services import project as project_service
from app.services.clauserisk import contracts as contract_service
from app.services.clauserisk import pipeline as pipeline_service
from app.services.clauserisk.access import ClauseRiskNotFoundError, get_owned_version

router = APIRouter(tags=["clauserisk-contracts"])


async def _require_clauserisk(db: AsyncSession, *, organization_id: str) -> None:
    try:
        await license_service.check_module_entitlement(
            db, organization_id=organization_id, module=LicenseModule.CLAUSERISK
        )
    except license_service.ModuleNotEntitledError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/contracts",
    response_model=ContractRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_contract(
    project_id: str,
    data: ContractCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractRead:
    await _require_clauserisk(db, organization_id=principal.organization.id)
    try:
        await project_service.get_project(
            db, organization_id=principal.organization.id, project_id=project_id
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found."
        ) from exc

    try:
        await license_service.check_contract_limit(db, organization_id=principal.organization.id)
    except license_service.UsageLimitExceededError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc

    contract = await contract_service.create_contract(
        db,
        organization_id=principal.organization.id,
        project_id=project_id,
        created_by_user_id=principal.user.id,
        data=data,
    )
    return ContractRead.model_validate(contract)


@router.get("/api/projects/{project_id}/contracts", response_model=list[ContractRead])
async def list_contracts(
    project_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[ContractRead]:
    await _require_clauserisk(db, organization_id=principal.organization.id)
    try:
        await project_service.get_project(
            db, organization_id=principal.organization.id, project_id=project_id
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Project not found."
        ) from exc
    contracts = await contract_service.list_contracts(db, project_id=project_id)
    return [ContractRead.model_validate(c) for c in contracts]


@router.get("/api/contracts", response_model=list[ContractListItem])
async def list_all_contracts(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[ContractListItem]:
    """Contracts across every project in the organization — backs the
    top-level Contracts nav item. list_contracts above (scoped to one
    project) remains the endpoint the Project detail page's Contracts
    section uses."""
    await _require_clauserisk(db, organization_id=principal.organization.id)
    rows = await contract_service.list_contracts_for_organization(
        db, organization_id=principal.organization.id
    )
    return [
        ContractListItem(**ContractRead.model_validate(contract).model_dump(), project_name=project_name)
        for contract, project_name in rows
    ]


@router.get("/api/contracts/{contract_id}", response_model=ContractDetailRead)
async def get_contract(
    contract_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractDetailRead:
    try:
        contract = await contract_service.get_contract_detail(
            db, organization_id=principal.organization.id, contract_id=contract_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract not found."
        ) from exc
    return ContractDetailRead.model_validate(contract)


@router.patch("/api/contracts/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: str,
    data: ContractUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractRead:
    try:
        contract = await contract_service.update_contract(
            db, organization_id=principal.organization.id, contract_id=contract_id, data=data
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract not found."
        ) from exc
    return ContractRead.model_validate(contract)


@router.post(
    "/api/contracts/{contract_id}/versions",
    response_model=ContractVersionRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def upload_contract_version(
    contract_id: str,
    background_tasks: BackgroundTasks,
    version_label: str = Form(...),
    file: UploadFile = File(...),
    run_analysis: bool = Form(False),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractVersionRead:
    await _require_clauserisk(db, organization_id=principal.organization.id)
    try:
        await license_service.check_and_report_usage(
            db,
            organization_id=principal.organization.id,
            event_type="document_uploaded",
            limit_field="monthly_document_limit",
        )
    except license_service.UsageLimitExceededError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc

    content = await file.read()
    try:
        version = await contract_service.create_contract_version(
            db,
            organization_id=principal.organization.id,
            contract_id=contract_id,
            uploaded_by_user_id=principal.user.id,
            version_label=version_label,
            filename=file.filename or "contract",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract not found."
        ) from exc
    except document_service.InvalidUploadError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    background_tasks.add_task(document_service.run_extraction, version.document_id)

    if run_analysis:
        # Starting analysis in the same request lets "upload and analyse" be
        # one step even though extraction (OCR on a scan) takes minutes.
        try:
            await license_service.check_and_report_usage(
                db,
                organization_id=principal.organization.id,
                event_type="clause_analysis_run",
                limit_field="monthly_clause_analysis_limit",
            )
        except license_service.UsageLimitExceededError as exc:
            # The upload itself succeeded; say why analysis didn't start
            # rather than failing a request whose file is already stored.
            version.analysis_status = ContractAnalysisStatus.FAILED
            version.analysis_error = str(exc)
        else:
            pipeline_service.queue_analysis_after_extraction(version)
            background_tasks.add_task(pipeline_service.run_analysis_after_extraction, version.id)
        await db.commit()
        await db.refresh(version)

    return ContractVersionRead.model_validate(version)


@router.post("/api/contract-versions/{version_id}/analysis", response_model=ContractAnalysisStatusRead)
async def start_contract_analysis(
    version_id: str,
    background_tasks: BackgroundTasks,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractAnalysisStatusRead:
    await _require_clauserisk(db, organization_id=principal.organization.id)
    try:
        version = await pipeline_service.check_analysis_preconditions(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except pipeline_service.AnalysisPreconditionError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        await license_service.check_and_report_usage(
            db,
            organization_id=principal.organization.id,
            event_type="clause_analysis_run",
            limit_field="monthly_clause_analysis_limit",
        )
    except license_service.UsageLimitExceededError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc

    version.analysis_status = ContractAnalysisStatus.PROCESSING
    version.analysis_error = None
    version.analysis_started_at = utcnow()
    version.analysis_completed_at = None
    await db.commit()

    background_tasks.add_task(pipeline_service.run_contract_analysis, version_id)

    return ContractAnalysisStatusRead.model_validate(version, from_attributes=True)


@router.get("/api/contract-versions/{version_id}/analysis", response_model=ContractAnalysisStatusRead)
async def get_contract_analysis_status(
    version_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ContractAnalysisStatusRead:
    try:
        version = await get_owned_version(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract version not found."
        ) from exc
    return ContractAnalysisStatusRead.model_validate(version, from_attributes=True)


@router.get("/api/contract-versions/{version_id}/file")
async def get_contract_version_file(
    version_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """The contract file behind a version, so a finding's evidence can be
    opened at its page."""
    try:
        version = await get_owned_version(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract version not found."
        ) from exc
    await db.refresh(version, attribute_names=["document"])
    return document_file_response(version.document)


@router.get("/api/contract-versions/{version_id}/clauses", response_model=list[ClauseRead])
async def list_clauses(
    version_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[ClauseRead]:
    try:
        await get_owned_version(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract version not found."
        ) from exc
    clauses = await contract_service.list_clauses(db, contract_version_id=version_id)
    return [ClauseRead.model_validate(c) for c in clauses]


@router.get("/api/clauses/{clause_id}", response_model=ClauseDetailRead)
async def get_clause(
    clause_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ClauseDetailRead:
    try:
        clause = await contract_service.get_clause_detail(
            db, organization_id=principal.organization.id, clause_id=clause_id
        )
        links = await contract_service.get_clause_links(
            db, contract_version_id=clause.contract_version_id, clause_id=clause_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Clause not found."
        ) from exc
    result = ClauseDetailRead.model_validate(clause)
    result.links = [CrossClauseLinkRead.model_validate(link) for link in links]
    return result
