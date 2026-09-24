import enum
import json
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.clause import Clause
    from app.models.contract import ContractVersion
    from app.models.review_action import ReviewAction


class RiskSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class AffectedParty(str, enum.Enum):
    CONTRACTOR = "contractor"
    CLIENT = "client"
    BOTH = "both"
    THIRD_PARTY = "third_party"
    UNCLEAR = "unclear"


class RiskUncertainty(str, enum.Enum):
    EXPLICIT = "explicit"
    NOT_APPLICABLE = "not_applicable"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    REQUIRES_REVIEW = "requires_review"


class FindingReviewerStatus(str, enum.Enum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MARKED_FOR_NEGOTIATION = "marked_for_negotiation"
    REVIEWED = "reviewed"


def _json_list_default() -> str:
    return "[]"


class RiskFinding(TimestampMixin, Base):
    """clause_id is nullable: a "missing protection" finding (e.g. "no
    force majeure clause found anywhere in this contract") is inherently
    not attached to a single clause — see reliability principle "never
    treat 'not found' as proof a provision does not exist" in
    docs/architecture.md's ClauseRisk section.
    """

    __tablename__ = "risk_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contract_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_versions.id"), nullable=False, index=True
    )
    clause_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clauses.id"), nullable=True, index=True
    )

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(
        Enum(RiskSeverity, native_enum=False, length=20), nullable=False
    )
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)
    contractual_effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    potential_exposure: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_party: Mapped[AffectedParty] = mapped_column(
        Enum(AffectedParty, native_enum=False, length=20), default=AffectedParty.UNCLEAR, nullable=False
    )

    evidence: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    related_clauses: Mapped[str] = mapped_column(Text, default=_json_list_default, nullable=False)
    uncertainty: Mapped[RiskUncertainty] = mapped_column(
        Enum(RiskUncertainty, native_enum=False, length=20),
        default=RiskUncertainty.REQUIRES_REVIEW,
        nullable=False,
    )
    recommended_review_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_factors: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    computed_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    reviewer_status: Mapped[FindingReviewerStatus] = mapped_column(
        Enum(FindingReviewerStatus, native_enum=False, length=30),
        default=FindingReviewerStatus.UNREVIEWED,
        nullable=False,
    )
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    contract_version: Mapped["ContractVersion"] = relationship()
    clause: Mapped["Clause | None"] = relationship(back_populates="risk_findings")
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="risk_finding", cascade="all, delete-orphan", order_by="ReviewAction.created_at"
    )

    def get_evidence(self) -> list[dict]:
        return json.loads(self.evidence) if self.evidence else []

    def set_evidence(self, value: list[dict]) -> None:
        self.evidence = json.dumps(value)

    def get_related_clauses(self) -> list[str]:
        return json.loads(self.related_clauses) if self.related_clauses else []

    def get_risk_factors(self) -> dict:
        return json.loads(self.risk_factors) if self.risk_factors else {}
