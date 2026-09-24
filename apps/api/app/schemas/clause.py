import json

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.clause import SourceConfidence


def _parse_json_list(value: object) -> list[str]:
    if isinstance(value, str):
        return list(json.loads(value)) if value else []
    if isinstance(value, list):
        return value
    return []


class ClauseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_version_id: str
    clause_number: str | None
    title: str
    text: str
    page_start: int
    page_end: int
    sequence_index: int
    category: str | None
    subcategory: str | None
    source_confidence: SourceConfidence | None
    extraction_error: str | None

    referenced_clauses: list[str]
    extracted_obligations: list[str]
    extracted_rights: list[str]
    extracted_conditions: list[str]
    extracted_exceptions: list[str]
    extracted_amounts: list[str]
    extracted_dates: list[str]
    extracted_percentages: list[str]
    extracted_time_periods: list[str]

    _parse_lists = field_validator(
        "referenced_clauses",
        "extracted_obligations",
        "extracted_rights",
        "extracted_conditions",
        "extracted_exceptions",
        "extracted_amounts",
        "extracted_dates",
        "extracted_percentages",
        "extracted_time_periods",
        mode="before",
    )(_parse_json_list)


class CrossClauseLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clause_a_id: str
    clause_b_id: str
    relationship_type: str
    basis: str
    note: str | None


class ClauseDetailRead(ClauseRead):
    links: list[CrossClauseLinkRead] = []
