"""Cross-module dashboard aggregates.

One query set, server-side, rather than having the web app fetch every
project, contract, and finding and count them in the browser: the numbers
a bid or contract manager opens the app to see (what closes soonest, what
is waiting on me, where the risk is concentrated) shouldn't cost four
round-trips and grow linearly with the account's data.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus, Priority
from app.models.contract import Contract, ContractAnalysisStatus, ContractVersion
from app.models.project import Project, ProjectStatus
from app.models.requirement import Requirement
from app.models.risk_finding import FindingReviewerStatus, RiskFinding, RiskSeverity

UPCOMING_DEADLINE_LIMIT = 5


@dataclass
class UpcomingDeadline:
    project_id: str
    name: str
    client_name: str | None
    submission_deadline: date
    days_remaining: int


@dataclass
class DashboardSummary:
    projects_total: int = 0
    projects_active: int = 0
    requirements_awaiting_review: int = 0
    critical_requirements: int = 0
    overdue_deadlines: int = 0
    upcoming_deadlines: list[UpcomingDeadline] = field(default_factory=list)
    contracts_total: int = 0
    contracts_analyzed: int = 0
    findings_unreviewed: int = 0
    findings_by_severity: dict[str, int] = field(default_factory=dict)


def _org_projects(organization_id: str) -> Select:
    return select(Project.id).where(
        Project.organization_id == organization_id, Project.deleted_at.is_(None)
    )


async def get_dashboard_summary(
    db: AsyncSession, *, organization_id: str, today: date | None = None
) -> DashboardSummary:
    today = today or date.today()
    summary = DashboardSummary()
    project_ids = _org_projects(organization_id)

    summary.projects_total = (
        await db.scalar(select(func.count()).select_from(project_ids.subquery())) or 0
    )
    summary.projects_active = (
        await db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
                Project.status == ProjectStatus.ACTIVE,
            )
        )
        or 0
    )

    # Requirements still needing a human decision: the AI flagged them for
    # review and nobody has recorded one yet.
    summary.requirements_awaiting_review = (
        await db.scalar(
            select(func.count())
            .select_from(Assessment)
            .join(Requirement, Assessment.requirement_id == Requirement.id)
            .where(
                Requirement.project_id.in_(project_ids),
                Assessment.requires_human_review.is_(True),
                Assessment.reviewer_status == "unreviewed",
            )
        )
        or 0
    )
    summary.critical_requirements = (
        await db.scalar(
            select(func.count())
            .select_from(Assessment)
            .join(Requirement, Assessment.requirement_id == Requirement.id)
            .where(
                Requirement.project_id.in_(project_ids),
                Assessment.priority == Priority.CRITICAL,
                Assessment.status.notin_(
                    [AssessmentStatus.HUMAN_VERIFIED, AssessmentStatus.HUMAN_REJECTED]
                ),
            )
        )
        or 0
    )

    # Deadlines: only projects still being worked on. A submitted or
    # archived tender's past deadline isn't an alert, it's history.
    open_statuses = [ProjectStatus.DRAFT, ProjectStatus.ACTIVE]
    summary.overdue_deadlines = (
        await db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
                Project.status.in_(open_statuses),
                Project.submission_deadline.is_not(None),
                Project.submission_deadline < today,
            )
        )
        or 0
    )

    deadline_rows = await db.execute(
        select(Project.id, Project.name, Project.client_name, Project.submission_deadline)
        .where(
            Project.organization_id == organization_id,
            Project.deleted_at.is_(None),
            Project.status.in_(open_statuses),
            Project.submission_deadline.is_not(None),
            Project.submission_deadline >= today,
        )
        .order_by(Project.submission_deadline)
        .limit(UPCOMING_DEADLINE_LIMIT)
    )
    summary.upcoming_deadlines = [
        UpcomingDeadline(
            project_id=row_id,
            name=name,
            client_name=client_name,
            submission_deadline=deadline,
            days_remaining=(deadline - today).days,
        )
        for row_id, name, client_name, deadline in deadline_rows.all()
    ]

    org_contracts = (
        select(Contract.id)
        .join(Project, Contract.project_id == Project.id)
        .where(
            Project.organization_id == organization_id,
            Project.deleted_at.is_(None),
            Contract.deleted_at.is_(None),
        )
    )
    summary.contracts_total = (
        await db.scalar(select(func.count()).select_from(org_contracts.subquery())) or 0
    )
    summary.contracts_analyzed = (
        await db.scalar(
            select(func.count(func.distinct(ContractVersion.contract_id))).where(
                ContractVersion.contract_id.in_(org_contracts),
                ContractVersion.analysis_status == ContractAnalysisStatus.COMPLETED,
            )
        )
        or 0
    )

    severity_rows = await db.execute(
        select(RiskFinding.severity, func.count())
        .join(ContractVersion, RiskFinding.contract_version_id == ContractVersion.id)
        .where(ContractVersion.contract_id.in_(org_contracts))
        .group_by(RiskFinding.severity)
    )
    counts = {severity.value: 0 for severity in RiskSeverity}
    for severity, count in severity_rows.all():
        key = severity.value if isinstance(severity, RiskSeverity) else str(severity)
        counts[key] = count
    summary.findings_by_severity = counts

    summary.findings_unreviewed = (
        await db.scalar(
            select(func.count())
            .select_from(RiskFinding)
            .join(ContractVersion, RiskFinding.contract_version_id == ContractVersion.id)
            .where(
                ContractVersion.contract_id.in_(org_contracts),
                RiskFinding.reviewer_status == FindingReviewerStatus.UNREVIEWED,
            )
        )
        or 0
    )

    return summary
