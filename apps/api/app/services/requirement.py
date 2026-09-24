from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.review_action import ReviewAction
from app.schemas.requirement import ReviewActionCreate
from app.services import project as project_service


class RequirementNotFoundError(Exception):
    pass


async def list_requirements(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    status: str | None = None,
    mandatory_status: str | None = None,
    priority: str | None = None,
    reviewer_status: str | None = None,
    search: str | None = None,
) -> list[Requirement]:
    await project_service.get_project(db, organization_id=organization_id, project_id=project_id)

    query = (
        select(Requirement)
        .where(Requirement.project_id == project_id)
        .options(selectinload(Requirement.assessment))
        .join(Assessment, Assessment.requirement_id == Requirement.id, isouter=True)
    )
    if status:
        query = query.where(Assessment.status == status)
    if mandatory_status:
        query = query.where(Requirement.mandatory_status == mandatory_status)
    if priority:
        query = query.where(Assessment.priority == priority)
    if reviewer_status:
        query = query.where(Assessment.reviewer_status == reviewer_status)
    if search:
        like = f"%{search}%"
        query = query.where(
            Requirement.title.ilike(like)
            | Requirement.normalized_requirement.ilike(like)
            | Requirement.source_clause.ilike(like)
        )

    query = query.order_by(Requirement.source_page, Requirement.created_at)
    result = await db.scalars(query)
    return list(result.unique())


async def get_requirement_detail(
    db: AsyncSession, *, organization_id: str, requirement_id: str
) -> Requirement:
    requirement = await db.scalar(
        select(Requirement)
        .where(Requirement.id == requirement_id)
        .options(
            selectinload(Requirement.assessment),
            selectinload(Requirement.evidence_records),
            selectinload(Requirement.review_actions),
        )
    )
    if requirement is None:
        raise RequirementNotFoundError(requirement_id)

    # tenant scoping: the requirement's project must belong to this org
    project = await db.get(Project, requirement.project_id)
    if project is None or project.organization_id != organization_id:
        raise RequirementNotFoundError(requirement_id)

    return requirement


async def apply_review_action(
    db: AsyncSession,
    *,
    organization_id: str,
    requirement_id: str,
    user_id: str,
    data: ReviewActionCreate,
) -> Requirement:
    requirement = await get_requirement_detail(
        db, organization_id=organization_id, requirement_id=requirement_id
    )
    assessment = requirement.assessment
    if assessment is None:
        raise RequirementNotFoundError(requirement_id)

    previous_status = assessment.status
    if data.new_status is not None:
        assessment.status = data.new_status
        assessment.reviewer_status = "reviewed"
        assessment.reviewer_user_id = user_id
        assessment.requires_human_review = False

    # Append through the relationship (not just db.add() with the FK set) so
    # the in-memory `requirement.review_actions` collection — already loaded
    # by get_requirement_detail's selectinload above — reflects the new row
    # immediately. A bare db.add() leaves that already-loaded collection
    # stale in this session's identity map even after commit + re-query.
    # Append through the relationship (not db.add() with the FK set directly)
    # so the in-memory `requirement.review_actions` collection — already
    # loaded by get_requirement_detail's selectinload above — reflects the
    # new row immediately. This session's sessionmaker uses
    # expire_on_commit=False, so no refresh/re-query is needed afterward.
    requirement.review_actions.append(
        ReviewAction(
            user_id=user_id,
            action_type="status_change" if data.new_status else "comment",
            previous_status=previous_status if data.new_status else None,
            new_status=data.new_status,
            comment=data.comment,
        )
    )
    await db.commit()

    # No refresh/re-query needed: this session's sessionmaker uses
    # expire_on_commit=False, and every change above (assessment attributes,
    # the appended review_actions item) was made in-memory on objects
    # already in this session's identity map — commit() persists them
    # without needing to reload anything.
    return requirement
