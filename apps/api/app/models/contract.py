import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.project import Project


class ContractType(str, enum.Enum):
    COMMERCIAL = "commercial"
    EPC = "epc"
    OIL_AND_GAS = "oil_and_gas"
    ENGINEERING = "engineering"
    CONSTRUCTION = "construction"
    SERVICES = "services"
    OTHER = "other"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType, native_enum=False, length=20), default=ContractType.OTHER, nullable=False
    )
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, native_enum=False, length=20),
        default=ContractStatus.DRAFT,
        nullable=False,
    )
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship()
    versions: Mapped[list["ContractVersion"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractVersion.version_number",
    )


class ContractAnalysisStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContractVersion(TimestampMixin, Base):
    __tablename__ = "contract_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contract_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contracts.id"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    version_number: Mapped[int] = mapped_column(nullable=False)
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)

    analysis_status: Mapped[ContractAnalysisStatus] = mapped_column(
        Enum(ContractAnalysisStatus, native_enum=False, length=20),
        default=ContractAnalysisStatus.NOT_STARTED,
        nullable=False,
    )
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    analysis_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Real progress, not a fake percentage. A 34-clause contract against a
    # local model takes over an hour (see docs/ai-evaluation.md), and a bare
    # "Processing" badge for that long is indistinguishable from a hung job.
    # The pipeline writes these as it goes so a reviewer can see it moving.
    analysis_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    analysis_progress_current: Mapped[int] = mapped_column(default=0, nullable=False)
    analysis_progress_total: Mapped[int] = mapped_column(default=0, nullable=False)

    contract: Mapped["Contract"] = relationship(back_populates="versions")
    document: Mapped["Document"] = relationship()
