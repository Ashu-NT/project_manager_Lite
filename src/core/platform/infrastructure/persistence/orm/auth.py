"""Platform ORM models for authentication and authorization."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from src.core.platform.domain.master_data.employee import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("identity_provider", "federated_subject", name="ux_users_federated_identity"),
        CheckConstraint(
            "account_type IN ('human', 'service')",
            name="ck_users_account_type",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="human",
        server_default="human",
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    identity_provider: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    federated_subject: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    session_timeout_minutes_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    session_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    last_login_auth_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_login_device_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_users_username", UserORM.username, unique=True)


class AuthSessionORM(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    auth_method: Mapped[str] = mapped_column(String(64), nullable=False)
    device_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    last_active_tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_active_organization_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_auth_sessions_user", AuthSessionORM.user_id)
Index("idx_auth_sessions_expires", AuthSessionORM.expires_at)
Index("idx_auth_sessions_revoked", AuthSessionORM.revoked_at)


class AuthPolicyReconciliationORM(Base):
    __tablename__ = "auth_policy_reconciliations"
    __table_args__ = (
        UniqueConstraint(
            "policy_name",
            "to_version",
            name="ux_auth_policy_reconciliation_version",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    from_version: Mapped[int] = mapped_column(Integer, nullable=False)
    to_version: Mapped[int] = mapped_column(Integer, nullable=False)
    change_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    applied_by_user_id: Mapped[str] = mapped_column(String, nullable=False)
    rollback_json: Mapped[str] = mapped_column(Text, nullable=False)


class RoleORM(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "(is_system AND tenant_id IS NULL) OR "
            "(NOT is_system AND tenant_id IS NOT NULL)",
            name="ck_roles_ownership",
        ),
        CheckConstraint(
            "is_system OR allowed_scope_type <> 'platform'",
            name="ck_roles_custom_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    allowed_scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_assignable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_roles_tenant", RoleORM.tenant_id)
Index(
    "ux_roles_system_name",
    RoleORM.name,
    unique=True,
    sqlite_where=RoleORM.tenant_id.is_(None),
    postgresql_where=RoleORM.tenant_id.is_(None),
)
Index(
    "ux_roles_tenant_name",
    RoleORM.tenant_id,
    RoleORM.name,
    unique=True,
    sqlite_where=RoleORM.tenant_id.is_not(None),
    postgresql_where=RoleORM.tenant_id.is_not(None),
)


class RoleBindingORM(Base):
    __tablename__ = "role_bindings"
    __table_args__ = (
        CheckConstraint(
            "principal_type = 'user'",
            name="ck_role_bindings_principal_type",
        ),
        CheckConstraint(
            "("
            "actual_scope_type = 'platform' AND tenant_id IS NULL "
            "AND actual_scope_id IS NULL"
            ") OR ("
            "actual_scope_type = 'tenant' AND tenant_id IS NOT NULL "
            "AND actual_scope_id IS NULL"
            ") OR ("
            "actual_scope_type NOT IN ('platform', 'tenant') "
            "AND tenant_id IS NOT NULL AND actual_scope_id IS NOT NULL"
            ")",
            name="ck_role_bindings_scope_shape",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_role_bindings_version_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    actual_scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actual_scope_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assigned_by: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )


Index("idx_role_bindings_principal", RoleBindingORM.principal_type, RoleBindingORM.principal_id)
Index("idx_role_bindings_role", RoleBindingORM.role_id)
Index("idx_role_bindings_tenant", RoleBindingORM.tenant_id)
Index(
    "ux_role_bindings_active_platform",
    RoleBindingORM.principal_type,
    RoleBindingORM.principal_id,
    RoleBindingORM.role_id,
    unique=True,
    sqlite_where=RoleBindingORM.revoked_at.is_(None)
    & (RoleBindingORM.actual_scope_type == "platform"),
    postgresql_where=RoleBindingORM.revoked_at.is_(None)
    & (RoleBindingORM.actual_scope_type == "platform"),
)
Index(
    "ux_role_bindings_active_tenant",
    RoleBindingORM.principal_type,
    RoleBindingORM.principal_id,
    RoleBindingORM.role_id,
    RoleBindingORM.tenant_id,
    unique=True,
    sqlite_where=RoleBindingORM.revoked_at.is_(None)
    & (RoleBindingORM.actual_scope_type == "tenant"),
    postgresql_where=RoleBindingORM.revoked_at.is_(None)
    & (RoleBindingORM.actual_scope_type == "tenant"),
)
Index(
    "ux_role_bindings_active_resource",
    RoleBindingORM.principal_type,
    RoleBindingORM.principal_id,
    RoleBindingORM.role_id,
    RoleBindingORM.tenant_id,
    RoleBindingORM.actual_scope_type,
    RoleBindingORM.actual_scope_id,
    unique=True,
    sqlite_where=RoleBindingORM.revoked_at.is_(None)
    & RoleBindingORM.actual_scope_type.not_in(("platform", "tenant")),
    postgresql_where=RoleBindingORM.revoked_at.is_(None)
    & RoleBindingORM.actual_scope_type.not_in(("platform", "tenant")),
)


class RoleDelegationPolicyORM(Base):
    __tablename__ = "role_delegation_policies"
    __table_args__ = (
        CheckConstraint(
            "assignable_role_policy_version >= 1",
            name="ck_role_delegation_policy_version_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    actor_role_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignable_role_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    assignable_role_policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    assignable_permission_set_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )


Index(
    "idx_role_delegation_actor",
    RoleDelegationPolicyORM.actor_role_id,
)
Index(
    "idx_role_delegation_assignable",
    RoleDelegationPolicyORM.assignable_role_id,
)
Index(
    "idx_role_delegation_tenant",
    RoleDelegationPolicyORM.tenant_id,
)
Index(
    "ux_role_delegation_active_system",
    RoleDelegationPolicyORM.actor_role_id,
    RoleDelegationPolicyORM.assignable_role_id,
    RoleDelegationPolicyORM.target_scope_type,
    unique=True,
    sqlite_where=RoleDelegationPolicyORM.revoked_at.is_(None)
    & RoleDelegationPolicyORM.tenant_id.is_(None),
    postgresql_where=RoleDelegationPolicyORM.revoked_at.is_(None)
    & RoleDelegationPolicyORM.tenant_id.is_(None),
)
Index(
    "ux_role_delegation_active_tenant",
    RoleDelegationPolicyORM.tenant_id,
    RoleDelegationPolicyORM.actor_role_id,
    RoleDelegationPolicyORM.assignable_role_id,
    RoleDelegationPolicyORM.target_scope_type,
    unique=True,
    sqlite_where=RoleDelegationPolicyORM.revoked_at.is_(None)
    & RoleDelegationPolicyORM.tenant_id.is_not(None),
    postgresql_where=RoleDelegationPolicyORM.revoked_at.is_(None)
    & RoleDelegationPolicyORM.tenant_id.is_not(None),
)


class PermissionORM(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")


Index("idx_permissions_code", PermissionORM.code, unique=True)


class RolePermissionORM(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="ux_role_permissions_role_perm"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[str] = mapped_column(String, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)


Index("idx_role_permissions_role", RolePermissionORM.role_id)
