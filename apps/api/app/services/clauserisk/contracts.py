from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clause import Clause
from app.models.contract import Contract, ContractVersion
from app.models.cross_clause_link import CrossClauseLink
from app.models.document import DocumentType
from app.models.project import Project
from app.models.risk_finding import RiskFinding
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services import document as document_service
from app.services.clauserisk.access import (
    ClauseRiskNotFoundError,
    get_owned_clause,
    get_owned_contract,
    get_owned_finding,
)


async def create_contract(
    db: AsyncSession, *, organization_id: str, project_id: str, created_by_user_id: str, data: ContractCreate
) -> Contract:
    contract = Contract(
        project_id=project_id,
        created_by_user_id=created_by_user_id,
        **data.model_dump(),
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def list_contracts(db: AsyncSession, *, project_id: str) -> list[Contract]:
    result = await db.scalars(
        select(Contract)
        .where(Contract.project_id == project_id, Contract.deleted_at.is_(None))
        .order_by(Contract.created_at.desc())
    )
    return list(result)


async def list_contracts_for_organization(
    db: AsyncSession, *, organization_id: str
) -> list[tuple[Contract, str]]:
    """Contracts across every project in the organization, each paired with
    its parent project's name — backs the top-level Contracts nav item,
    which (unlike list_contracts above) isn't scoped to one project."""
    result = await db.execute(
        select(Contract, Project.name)
        .join(Project, Contract.project_id == Project.id)
        .where(Project.organization_id == organization_id, Contract.deleted_at.is_(None))
        .order_by(Contract.created_at.desc())
    )
    return [(contract, project_name) for contract, project_name in result.all()]


async def get_contract_detail(db: AsyncSession, *, organization_id: str, contract_id: str) -> Contract:
    contract = await get_owned_contract(db, organization_id=organization_id, contract_id=contract_id)
    await db.refresh(contract, attribute_names=["versions"])
    return contract


async def update_contract(
    db: AsyncSession, *, organization_id: str, contract_id: str, data: ContractUpdate
) -> Contract:
    contract = await get_owned_contract(db, organization_id=organization_id, contract_id=contract_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)
    await db.commit()
    await db.refresh(contract)
    return contract


async def create_contract_version(
    db: AsyncSession,
    *,
    organization_id: str,
    contract_id: str,
    uploaded_by_user_id: str,
    version_label: str,
    filename: str,
    content: bytes,
    mime_type: str,
) -> ContractVersion:
    contract = await get_owned_contract(db, organization_id=organization_id, contract_id=contract_id)

    # Reuse TenderGuard's document storage + PyMuPDF extraction pipeline
    # wholesale — a contract PDF is uploaded and extracted exactly like a
    # tender/bid PDF, just tagged DocumentType.CONTRACT.
    document = await document_service.create_document(
        db,
        organization_id=organization_id,
        project_id=contract.project_id,
        uploaded_by_user_id=uploaded_by_user_id,
        document_type=DocumentType.CONTRACT,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )

    existing_version_count = await db.scalar(
        select(func.count()).select_from(ContractVersion).where(ContractVersion.contract_id == contract_id)
    )

    version = ContractVersion(
        contract_id=contract_id,
        document_id=document.id,
        uploaded_by_user_id=uploaded_by_user_id,
        version_number=(existing_version_count or 0) + 1,
        version_label=version_label,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def list_clauses(
    db: AsyncSession, *, contract_version_id: str, category: str | None = None
) -> list[Clause]:
    query = (
        select(Clause)
        .where(Clause.contract_version_id == contract_version_id)
        .order_by(Clause.sequence_index)
    )
    if category:
        query = query.where(Clause.category == category)
    result = await db.scalars(query)
    return list(result)


async def get_clause_detail(db: AsyncSession, *, organization_id: str, clause_id: str) -> Clause:
    return await get_owned_clause(db, organization_id=organization_id, clause_id=clause_id)


async def get_clause_links(
    db: AsyncSession, *, contract_version_id: str, clause_id: str
) -> list[CrossClauseLink]:
    result = await db.scalars(
        select(CrossClauseLink).where(
            CrossClauseLink.contract_version_id == contract_version_id,
            (CrossClauseLink.clause_a_id == clause_id) | (CrossClauseLink.clause_b_id == clause_id),
        )
    )
    return list(result)


async def list_risk_findings(
    db: AsyncSession,
    *,
    contract_version_id: str,
    severity: str | None = None,
    category: str | None = None,
    reviewer_status: str | None = None,
    clause_id: str | None = None,
) -> list[RiskFinding]:
    query = (
        select(RiskFinding)
        .where(RiskFinding.contract_version_id == contract_version_id)
        .options(selectinload(RiskFinding.clause))
        .order_by(RiskFinding.computed_score.desc())
    )
    if severity:
        query = query.where(RiskFinding.severity == severity)
    if category:
        query = query.where(RiskFinding.category == category)
    if reviewer_status:
        query = query.where(RiskFinding.reviewer_status == reviewer_status)
    if clause_id:
        query = query.where(RiskFinding.clause_id == clause_id)
    result = await db.scalars(query)
    return list(result.unique())


async def list_risk_findings_for_organization(
    db: AsyncSession,
    *,
    organization_id: str,
    severity: str | None = None,
    category: str | None = None,
    reviewer_status: str | None = None,
) -> list[tuple[RiskFinding, str, str, str | None]]:
    """Findings across every contract in the organization, each paired with
    its contract's id/name and (if attached to one) clause number — backs
    the top-level Risk Register, which spans contracts rather than being
    scoped to a single contract version like list_risk_findings above."""
    query = (
        select(RiskFinding, Contract.id, Contract.name, Clause.clause_number)
        .join(ContractVersion, RiskFinding.contract_version_id == ContractVersion.id)
        .join(Contract, ContractVersion.contract_id == Contract.id)
        .join(Project, Contract.project_id == Project.id)
        .outerjoin(Clause, RiskFinding.clause_id == Clause.id)
        .where(Project.organization_id == organization_id, Contract.deleted_at.is_(None))
        .order_by(RiskFinding.computed_score.desc())
    )
    if severity:
        query = query.where(RiskFinding.severity == severity)
    if category:
        query = query.where(RiskFinding.category == category)
    if reviewer_status:
        query = query.where(RiskFinding.reviewer_status == reviewer_status)
    result = await db.execute(query)
    return [(finding, cid, cname, cnum) for finding, cid, cname, cnum in result.all()]


async def get_finding_detail(db: AsyncSession, *, organization_id: str, finding_id: str) -> RiskFinding:
    finding = await get_owned_finding(db, organization_id=organization_id, finding_id=finding_id)
    await db.refresh(finding, attribute_names=["review_actions"])
    return finding


__all__ = ["ClauseRiskNotFoundError"]
