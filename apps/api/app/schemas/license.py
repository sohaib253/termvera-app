import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

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

    @field_validator("enabled_modules", mode="before")
    @classmethod
    def _parse_modules(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return list(json.loads(value)) if value else []
        if isinstance(value, list):
            return value
        return []


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
