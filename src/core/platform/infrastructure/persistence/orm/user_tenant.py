from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class UserTenantORM(Base):
    __tablename__ = "user_tenants"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="ux_user_tenants_user_tenant"),
        CheckConstraint(
            "status IN ('invited', 'active', 'suspended', 'removed')",
            name="ck_user_tenants_status",
        ),
        CheckConstraint(
            "(status = 'active' AND is_active) OR "
            "(status <> 'active' AND NOT is_active)",
            name="ck_user_tenants_active_status",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_user_tenants_version_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    tenant_role: Mapped[str] = mapped_column(
        String(64), nullable=False, default="member", server_default="member"
    )
    invited_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invitation_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )


Index("idx_user_tenants_user", UserTenantORM.user_id)
Index("idx_user_tenants_tenant", UserTenantORM.tenant_id)
Index("idx_user_tenants_active", UserTenantORM.is_active)
Index("idx_user_tenants_status", UserTenantORM.status)
Index(
    "idx_user_tenants_invitation_expiry",
    UserTenantORM.invitation_expires_at,
)


__all__ = ["UserTenantORM"]
