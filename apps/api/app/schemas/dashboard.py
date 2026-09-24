from datetime import date

from pydantic import BaseModel, ConfigDict


class UpcomingDeadlineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    name: str
    client_name: str | None
    submission_deadline: date
    days_remaining: int


class DashboardSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    projects_total: int
    projects_active: int
    requirements_awaiting_review: int
    critical_requirements: int
    overdue_deadlines: int
    upcoming_deadlines: list[UpcomingDeadlineRead]
    contracts_total: int
    contracts_analyzed: int
    findings_unreviewed: int
    findings_by_severity: dict[str, int]
