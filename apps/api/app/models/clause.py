import enum
import json
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.contract import ContractVersion
    from app.models.risk_finding import RiskFinding


class SourceConfidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _json_list_default() -> str:
    return "[]"


class Clause(TimestampMixin, Base):
    """One segmented clause of a contract version.

    Segmentation (finding clause boundaries) is deterministic — see
    app/services/clauserisk/segmentation.py — clause_number/title/text/
    page_start/page_end come from that, not from the AI. category through
    source_confidence are populated by the AI extraction stage and are
    only ever a candidate interpretation, never treated as the clause's
    "real" boundaries.

    List-shaped fields (referenced_clauses, extracted_*) are stored as
    JSON text for the same reason app/models/assessment.py stores
    missing_information as JSON — SQLite (used in tests) has no native
    array type, and Postgres JSON support isn't needed for the query
    patterns this app actually does (filtering by category/confidence,
    not by array membership).
    """

    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contract_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_versions.id"), nullable=False, index=True
    )

    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)

    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referenced_clauses: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_obligations: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_rights: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_conditions: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_exceptions: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_amounts: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_dates: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_percentages: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    extracted_time_periods: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    source_confidence: Mapped[SourceConfidence | None] = mapped_column(
        Enum(SourceConfidence, native_enum=False, length=10), nullable=True
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    contract_version: Mapped["ContractVersion"] = relationship()
    risk_findings: Mapped[list["RiskFinding"]] = relationship(
        back_populates="clause", cascade="all, delete-orphan"
    )

    def set_list_field(self, field: str, values: list[str]) -> None:
        setattr(self, field, json.dumps(values))

    def get_list_field(self, field: str) -> list[str]:
        raw = getattr(self, field)
        return json.loads(raw) if raw else []
