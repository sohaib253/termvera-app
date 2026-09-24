from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.contract import Contract
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectNotFoundError(Exception):
    pass


async def create_project(
    db: AsyncSession, *, organization_id: str, created_by_user_id: str, data: ProjectCreate
) -> Project:
    project = Project(
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        **data.model_dump(),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(db: AsyncSession, *, organization_id: str) -> list[Project]:
    result = await db.scalars(
        select(Project)
        .where(Project.organization_id == organization_id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )
    return list(result)


async def get_project(
    db: AsyncSession, *, organization_id: str, project_id: str
) -> Project:
    project = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
            Project.deleted_at.is_(None),
        )
    )
    if project is None:
        raise ProjectNotFoundError(project_id)
    return project


async def delete_project(db: AsyncSession, *, organization_id: str, project_id: str) -> None:
    """Soft delete. The project's documents, requirements, contracts, and
    findings are all reachable only through the project, so marking it
    deleted removes the whole tree from every list and detail route without
    destroying an audit trail someone may still need to answer for.
    Contracts are stamped too, because the org-wide Contracts list and Risk
    Register query contracts directly rather than through the project."""
    project = await get_project(db, organization_id=organization_id, project_id=project_id)
    deleted_at = utcnow()
    project.deleted_at = deleted_at
    await db.execute(
        update(Contract)
        .where(Contract.project_id == project.id, Contract.deleted_at.is_(None))
        .values(deleted_at=deleted_at)
    )
    await db.commit()


async def update_project(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    data: ProjectUpdate,
) -> Project:
    project = await get_project(db, organization_id=organization_id, project_id=project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project
