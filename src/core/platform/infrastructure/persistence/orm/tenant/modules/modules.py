"""Platform ORM models for module entitlements."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ModuleEntitlementORM(Base):
    __tablename__ = "organization_module_entitlements"

    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    module_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
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
Index("idx_org_module_entitlements_tenant", ModuleEntitlementORM.tenant_id)
