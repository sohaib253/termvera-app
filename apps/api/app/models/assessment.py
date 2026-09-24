import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.requirement import Requirement


class AssessmentStatus(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    COMPLIANT_LOOKING = "compliant_looking"
    PARTIALLY_ADDRESSED = "partially_addressed"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    POTENTIAL_NON_COMPLIANCE = "potential_non_compliance"
    NOT_APPLICABLE_PENDING_VERIFICATION = "not_applicable_pending_verification"
    HUMAN_VERIFIED = "human_verified"
    HUMAN_REJECTED = "human_rejected"


class EvidenceQuality(str, enum.Enum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    INSUFFICIENT = "insufficient"
    NONE = "none"
    UNKNOWN = "unknown"


class AssessmentConfidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Priority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, unique=True
    )

    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, native_enum=False, length=40),
        default=AssessmentStatus.NOT_ASSESSED,
        nullable=False,
    )
    evidence_quality: Mapped[EvidenceQuality] = mapped_column(
        Enum(EvidenceQuality, native_enum=False, length=20),
        default=EvidenceQuality.UNKNOWN,
        nullable=False,
    )
    assessment_confidence: Mapped[AssessmentConfidence] = mapped_column(
        Enum(AssessmentConfidence, native_enum=False, length=10),
        default=AssessmentConfidence.LOW,
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, length=20), default=Priority.MEDIUM, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    missing_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    reviewer_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False)
    reviewer_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    requirement: Mapped["Requirement"] = relationship(back_populates="assessment")
