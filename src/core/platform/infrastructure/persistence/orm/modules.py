"""Platform ORM models for module entitlements."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.org.domain import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class ModuleEntitlementORM(Base):
    __tablename__ = "organization_module_entitlements"

    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    module_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    licensed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    lifecycle_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="inactive",
        server_default="inactive",
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_org_module_entitlements_org", ModuleEntitlementORM.organization_id)
