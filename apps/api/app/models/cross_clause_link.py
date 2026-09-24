from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid

if TYPE_CHECKING:
    from app.models.clause import Clause


class CrossClauseLink(Base):
    """A deterministic (non-AI) link between two clauses in the same
    contract version — see app/services/clauserisk/cross_links.py. Built
    from explicit textual cross-references (e.g. "as defined in Clause
    12.3") and from configured category pairs known to interact (e.g.
    liquidated_damages <-> milestones). Used to give the risk-analysis AI
    call additional context for a clause, and surfaced in the UI so a
    reviewer can see why two clauses were considered together.
    """

    __tablename__ = "cross_clause_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contract_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_versions.id"), nullable=False, index=True
    )
    clause_a_id: Mapped[str] = mapped_column(String(36), ForeignKey("clauses.id"), nullable=False)
    clause_b_id: Mapped[str] = mapped_column(String(36), ForeignKey("clauses.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    basis: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "explicit_reference" | "category_pattern"
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    clause_a: Mapped["Clause"] = relationship(foreign_keys=[clause_a_id])
    clause_b: Mapped["Clause"] = relationship(foreign_keys=[clause_b_id])
