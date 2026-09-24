from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_action import ReviewAction
from app.models.risk_finding import RiskFinding
from app.schemas.risk_finding import FindingReviewActionCreate
from app.services.clauserisk.access import get_owned_finding


async def apply_finding_review_action(
    db: AsyncSession,
    *,
    organization_id: str,
    finding_id: str,
    user_id: str,
    data: FindingReviewActionCreate,
) -> RiskFinding:
    finding = await get_owned_finding(db, organization_id=organization_id, finding_id=finding_id)
    await db.refresh(finding, attribute_names=["review_actions"])

    previous_status = finding.reviewer_status
    action_type = "comment"
    if data.new_status is not None:
        finding.reviewer_status = data.new_status
        action_type = "status_change"
    if data.assign_to_user_id is not None:
        finding.assigned_to_user_id = data.assign_to_user_id
        action_type = "assignment" if action_type == "comment" else action_type

    # Append through the relationship, not db.add() with the FK set
    # directly — see docs/architecture.md's ClauseRisk section for the
    # identity-map staleness bug this avoids (first hit, and fixed, in
    # TenderGuard's equivalent app/services/requirement.py).
    finding.review_actions.append(
        ReviewAction(
            user_id=user_id,
            action_type=action_type,
            previous_status=previous_status if data.new_status else None,
            new_status=data.new_status,
            comment=data.comment,
        )
    )
    await db.commit()
    return finding
