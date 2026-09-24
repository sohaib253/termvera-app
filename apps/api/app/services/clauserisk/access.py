"""Tenant-scoping helpers shared by all ClauseRisk routes — mirrors how
app/api/routes/documents.py's `_ensure_project_access` and
app/services/requirement.py's `get_requirement_detail` scope TenderGuard
objects through their parent project. Every ClauseRisk object hangs off
a Contract, which hangs off a Project, which carries organization_id —
so every check below ultimately walks that chain.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clause import Clause
from app.models.contract import Contract, ContractVersion
from app.models.project import Project
from app.models.risk_finding import RiskFinding


class ClauseRiskNotFoundError(Exception):
    pass


async def get_owned_contract(db: AsyncSession, *, organization_id: str, contract_id: str) -> Contract:
    contract = await db.get(Contract, contract_id)
    if contract is None or contract.deleted_at is not None:
        raise ClauseRiskNotFoundError(contract_id)
    project = await db.get(Project, contract.project_id)
    if project is None or project.organization_id != organization_id:
        raise ClauseRiskNotFoundError(contract_id)
    return contract


async def get_owned_version(
    db: AsyncSession, *, organization_id: str, contract_version_id: str
) -> ContractVersion:
    version = await db.get(ContractVersion, contract_version_id)
    if version is None:
        raise ClauseRiskNotFoundError(contract_version_id)
    await get_owned_contract(db, organization_id=organization_id, contract_id=version.contract_id)
    return version


async def get_owned_clause(db: AsyncSession, *, organization_id: str, clause_id: str) -> Clause:
    clause = await db.get(Clause, clause_id)
    if clause is None:
        raise ClauseRiskNotFoundError(clause_id)
    await get_owned_version(
        db, organization_id=organization_id, contract_version_id=clause.contract_version_id
    )
    return clause


async def get_owned_finding(db: AsyncSession, *, organization_id: str, finding_id: str) -> RiskFinding:
    finding = await db.get(RiskFinding, finding_id)
    if finding is None:
        raise ClauseRiskNotFoundError(finding_id)
    await get_owned_version(
        db, organization_id=organization_id, contract_version_id=finding.contract_version_id
    )
    return finding
