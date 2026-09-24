from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.contract_comparison import ChangeType, Materiality


class CompareVersionsRequest(BaseModel):
    base_version_id: str
    compared_version_id: str


class ContractChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    change_type: ChangeType
    clause_number: str | None
    category: str | None
    base_clause_id: str | None
    compared_clause_id: str | None
    description: str
    materiality: Materiality
    financial_delta: str | None


class ContractComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    base_version_id: str
    compared_version_id: str
    created_at: datetime
    changes: list[ContractChangeRead]
