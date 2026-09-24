from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.requirement import Requirement


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_method: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    relevance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    potential_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)

    requirement: Mapped["Requirement"] = relationship(back_populates="evidence_records")
    document: Mapped["Document"] = relationship()
