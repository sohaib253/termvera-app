from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.requirement import Requirement
    from app.models.risk_finding import RiskFinding


class ReviewAction(TimestampMixin, Base):
    """Shared audit-trail table for both modules — a TenderGuard
    requirement review action has requirement_id set and risk_finding_id
    null; a ClauseRisk finding review action is the reverse. Exactly one
    of the two must be set (enforced by the CHECK constraint below and by
    each module's service layer, which only ever sets the one it owns)."""

    __tablename__ = "review_actions"
    __table_args__ = (
        CheckConstraint(
            "(requirement_id IS NOT NULL) != (risk_finding_id IS NOT NULL)",
            name="ck_review_action_exactly_one_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    requirement_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=True, index=True
    )
    risk_finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("risk_findings.id"), nullable=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    requirement: Mapped["Requirement | None"] = relationship(back_populates="review_actions")
    risk_finding: Mapped["RiskFinding | None"] = relationship(back_populates="review_actions")
