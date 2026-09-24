from datetime import datetime

from pydantic import BaseModel

from app.models.contract import ContractAnalysisStatus
from app.models.project import AnalysisStatus


class AnalysisStatusRead(BaseModel):
    analysis_status: AnalysisStatus
    analysis_error: str | None
    analysis_started_at: datetime | None
    analysis_completed_at: datetime | None


class ContractAnalysisStatusRead(BaseModel):
    """Same shape as AnalysisStatusRead, typed against ClauseRisk's own
    ContractAnalysisStatus enum — kept separate because the two enums,
    while string-identical today, belong to independent domains and
    should be free to diverge (e.g. a future PARTIAL status for
    per-clause failures) without coupling the two modules."""

    analysis_status: ContractAnalysisStatus
    analysis_error: str | None
    analysis_started_at: datetime | None
    analysis_completed_at: datetime | None
    # Present while processing: which stage is running and how far through it.
    analysis_stage: str | None = None
    analysis_progress_current: int = 0
    analysis_progress_total: int = 0
