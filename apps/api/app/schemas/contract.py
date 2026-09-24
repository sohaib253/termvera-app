from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.contract import ContractAnalysisStatus, ContractStatus, ContractType


class ContractCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contract_type: ContractType = ContractType.OTHER
    counterparty_name: str | None = None
    effective_date: date | None = None
    notes: str | None = None


class ContractUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    contract_type: ContractType | None = None
    status: ContractStatus | None = None
    counterparty_name: str | None = None
    effective_date: date | None = None
    notes: str | None = None


class ContractVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    document_id: str
    version_number: int
    version_label: str
    analysis_status: ContractAnalysisStatus
    analysis_error: str | None
    analysis_started_at: datetime | None
    analysis_completed_at: datetime | None
    analysis_stage: str | None
    analysis_progress_current: int
    analysis_progress_total: int
    created_at: datetime


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    contract_type: ContractType
    status: ContractStatus
    counterparty_name: str | None
    effective_date: date | None
    notes: str | None
    is_demo: bool
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class ContractDetailRead(ContractRead):
    versions: list[ContractVersionRead]


class ContractListItem(ContractRead):
    """ContractRead plus the parent project's name, for the org-wide
    Contracts list where the project isn't already implied by the URL."""

    project_name: str
