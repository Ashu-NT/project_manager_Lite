"""Platform ORM models for scoped access."""

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

from src.core.platform.employee.domain import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class ProjectMembershipORM(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="ux_project_memberships_project_user"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    scope_role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer", server_default="viewer")
    permission_codes_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_project_memberships_project", ProjectMembershipORM.project_id)
Index("idx_project_memberships_user", ProjectMembershipORM.user_id)
Index("idx_project_memberships_org", ProjectMembershipORM.organization_id)


class ScopedAccessGrantORM(Base):
    __tablename__ = "scoped_access_grants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scope_type", "scope_id", "user_id", name="ux_scoped_access_tenant_scope_user"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer", server_default="viewer")
    permission_codes_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_scoped_access_scope", ScopedAccessGrantORM.scope_type, ScopedAccessGrantORM.scope_id)
Index("idx_scoped_access_tenant", ScopedAccessGrantORM.tenant_id)
