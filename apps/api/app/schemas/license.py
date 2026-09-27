import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.license import LicensePlan, LicenseStatus


class LicenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: LicensePlan
    status: LicenseStatus
    seat_limit: int
    project_limit: int
    monthly_document_limit: int
    monthly_analysis_limit: int
    monthly_contract_limit: int
    monthly_clause_analysis_limit: int
    enabled_modules: list[str]
    expires_at: datetime | None

    # What the workspace may do right now; see license.get_entitlement.
    state: str = "trial"  # trial | trial_expired | active | grace | expired
    read_only: bool = False
    ends_at: datetime | None = None
    days_left: int | None = None
    licensed_to: str | None = None
    license_id: str | None = None
    # This computer's ID, for requesting a per-PC key; bound_machine_id is
    # set when the active key is tied to one computer.
    machine_id: str | None = None
    bound_machine_id: str | None = None

    @field_validator("enabled_modules", mode="before")
    @classmethod
    def _parse_modules(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return list(json.loads(value)) if value else []
        if isinstance(value, list):
            return value
        return []


class LicenseActivate(BaseModel):
    key: str = Field(min_length=10, max_length=4000)


class LicensePlanUpdate(BaseModel):
    plan: LicensePlan
    enabled_modules: list[str] | None = None


class UsageRead(BaseModel):
    license: LicenseRead
    projects_used: int
    documents_used_this_period: int
    analyses_used_this_period: int
    contracts_used: int
    clause_analyses_used_this_period: int
    period_start: datetime
