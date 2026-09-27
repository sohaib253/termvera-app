import enum
import json
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, utcnow

if TYPE_CHECKING:
    from app.models.organization import Organization


class LicensePlan(str, enum.Enum):
    # Early access: everything free while billing is switched off
    # (settings.billing_enabled). See app/services/license.py.
    FREE = "free"
    DEMO = "demo"
    TRIAL = "trial"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseModule(str, enum.Enum):
    """A licensed product module. An org's LicenseAccount.enabled_modules
    is a JSON list of these values — "modular" per the ClauseRisk brief:
    an org can be entitled to TenderGuard only, ClauseRisk only, or both."""

    TENDERGUARD = "tenderguard"
    CLAUSERISK = "clauserisk"


ALL_MODULES = [LicenseModule.TENDERGUARD.value, LicenseModule.CLAUSERISK.value]


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


# One row per workspace: its plan, limits, modules and, once activated, the
# signed license key that granted them. See docs/licensing.md.
class LicenseAccount(TimestampMixin, Base):
    __tablename__ = "license_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, unique=True
    )

    # New workspaces start on the time-limited trial; see
    # app/services/license.py::get_entitlement for how plan, trial and
    # license key combine into what the workspace may do.
    plan: Mapped[LicensePlan] = mapped_column(
        Enum(LicensePlan, native_enum=False, length=20), default=LicensePlan.TRIAL, nullable=False
    )
    status: Mapped[LicenseStatus] = mapped_column(
        Enum(LicenseStatus, native_enum=False, length=20),
        default=LicenseStatus.ACTIVE,
        nullable=False,
    )

    seat_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    project_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    monthly_document_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    monthly_analysis_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # ClauseRisk-specific limits, alongside the TenderGuard ones above.
    monthly_contract_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    monthly_clause_analysis_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # JSON list of LicenseModule values. Demo plan defaults to both
    # modules enabled so the out-of-the-box local experience isn't
    # gated — see docs/licensing.md for what a real paid-plan module
    # gate would need beyond this.
    enabled_modules: Mapped[str] = mapped_column(
        String(200), default=lambda: json.dumps(ALL_MODULES), nullable=False
    )

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Set by activating a signed license key (app/services/license_keys.py).
    license_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    licensee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The latest time this workspace has seen. Trial and license expiry are
    # judged against max(now, this), so winding the system clock back
    # doesn't extend them.
    clock_high_water: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship()

    def get_enabled_modules(self) -> list[str]:
        return json.loads(self.enabled_modules) if self.enabled_modules else []

    def has_module(self, module: "LicenseModule") -> bool:
        return module.value in self.get_enabled_modules()


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
