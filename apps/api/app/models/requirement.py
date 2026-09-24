import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.document import Document
    from app.models.evidence import EvidenceRecord
    from app.models.project import Project
    from app.models.review_action import ReviewAction


class MandatoryStatus(str, enum.Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    INDICATIVE = "indicative"
    UNCLEAR = "unclear"


class Requirement(TimestampMixin, Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    source_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )

    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    mandatory_status: Mapped[MandatoryStatus] = mapped_column(
        Enum(MandatoryStatus, native_enum=False, length=20), nullable=False
    )
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_uncertain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project: Mapped["Project"] = relationship()
    source_document: Mapped["Document"] = relationship()
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )
    assessment: Mapped["Assessment | None"] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", uselist=False
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", order_by="ReviewAction.created_at"
    )
