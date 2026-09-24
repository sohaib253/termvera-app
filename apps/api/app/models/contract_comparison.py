import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.contract import Contract, ContractVersion


class ChangeType(str, enum.Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"


class Materiality(str, enum.Enum):
    MATERIAL = "material"
    MINOR = "minor"


class ContractComparison(TimestampMixin, Base):
    __tablename__ = "contract_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contract_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contracts.id"), nullable=False, index=True
    )
    base_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_versions.id"), nullable=False
    )
    compared_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_versions.id"), nullable=False
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    contract: Mapped["Contract"] = relationship()
    base_version: Mapped["ContractVersion"] = relationship(foreign_keys=[base_version_id])
    compared_version: Mapped["ContractVersion"] = relationship(foreign_keys=[compared_version_id])
    changes: Mapped[list["ContractChange"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )


class ContractChange(Base):
    __tablename__ = "contract_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    comparison_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_comparisons.id"), nullable=False, index=True
    )

    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType, native_enum=False, length=20), nullable=False
    )
    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    base_clause_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clauses.id"), nullable=True
    )
    compared_clause_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clauses.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    materiality: Mapped[Materiality] = mapped_column(
        Enum(Materiality, native_enum=False, length=10), default=Materiality.MINOR, nullable=False
    )
    financial_delta: Mapped[str | None] = mapped_column(String(255), nullable=True)

    comparison: Mapped["ContractComparison"] = relationship(back_populates="changes")
