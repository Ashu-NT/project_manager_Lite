from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import UserTenantORM
from src.core.platform.contract.repositories.security.auth import (
    AuthPolicyReconciliationRepository,
    AuthSessionRepository,
    PermissionRepository,
    RoleBindingRepository,
    RoleDelegationPolicyRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.domain.security.authorization.roles import (
    AuthPolicyReconciliation,
    RoleBinding,
    RoleDelegationPolicy,
)
from src.core.platform.domain.security.auth import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    normalize_auth_session_context_id,
    normalize_auth_session_datetime,
)
from src.core.platform.infrastructure.persistence.mappers.security.auth.auth import (
    auth_session_from_orm,
    auth_session_to_orm,
    permission_from_orm,
    permission_to_orm,
    role_from_orm,
    role_binding_from_orm,
    role_binding_to_orm,
    role_delegation_policy_from_orm,
    role_delegation_policy_to_orm,
    role_permission_to_orm,
    role_to_orm,
    user_from_orm,
    user_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    AuthPolicyReconciliationORM,
    AuthSessionORM,
    PermissionORM,
    RoleBindingORM,
    RoleDelegationPolicyORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
)
from src.core.platform.domain.tenant.tenancy.user_tenant_membership import (
    MEMBERSHIP_STATUS_ACTIVE,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyUserRepository(UserRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: UserAccount) -> None:
        self.session.add(user_to_orm(user))

    def update(self, user: UserAccount) -> None:
        user.version = update_with_version_check(
            self.session,
            UserORM,
            user.id,
            getattr(user, "version", 1),
            {
                "username": user.username,
                "password_hash": user.password_hash,
                "account_type": getattr(user, "account_type", "human"),
                "display_name": user.display_name,
                "email": user.email,
                "identity_provider": getattr(user, "identity_provider", None),
                "federated_subject": getattr(user, "federated_subject", None),
                "mfa_secret": getattr(user, "mfa_secret", None),
                "mfa_enabled": getattr(user, "mfa_enabled", False),
                "session_timeout_minutes_override": getattr(user, "session_timeout_minutes_override", None),
                "session_revision": getattr(user, "session_revision", 1),
                "last_login_auth_method": getattr(user, "last_login_auth_method", None),
                "last_login_device_label": getattr(user, "last_login_device_label", None),
                "is_active": user.is_active,
                "failed_login_attempts": getattr(user, "failed_login_attempts", 0),
                "locked_until": getattr(user, "locked_until", None),
                "last_login_at": getattr(user, "last_login_at", None),
                "session_expires_at": getattr(user, "session_expires_at", None),
                "password_changed_at": getattr(user, "password_changed_at", None),
                "must_change_password": getattr(user, "must_change_password", False),
                "updated_at": user.updated_at,
            },
            not_found_message="User not found.",
            stale_message="User account was updated by another user.",
        )

    def get(self, user_id: str) -> UserAccount | None:
        obj = self.session.get(UserORM, user_id)
        return user_from_orm(obj) if obj else None

    def get_by_username(self, username: str) -> UserAccount | None:
        stmt = select(UserORM).where(UserORM.username == username)
        obj = self.session.execute(stmt).scalars().first()
        return user_from_orm(obj) if obj else None

    def get_by_federated_identity(
        self,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount | None:
        stmt = select(UserORM).where(
            UserORM.identity_provider == identity_provider,
            UserORM.federated_subject == federated_subject,
        )
        obj = self.session.execute(stmt).scalars().first()
        return user_from_orm(obj) if obj else None

    def list_all(self) -> list[UserAccount]:
        rows = self.session.execute(select(UserORM)).scalars().all()
        return [user_from_orm(row) for row in rows]

    def list_for_tenant(self, tenant_id: str) -> list[UserAccount]:
        stmt = (
            select(UserORM)
            .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
            .where(UserTenantORM.tenant_id == tenant_id)
            .where(UserTenantORM.status == MEMBERSHIP_STATUS_ACTIVE)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [user_from_orm(row) for row in rows]


class SqlAlchemyAuthSessionRepository(AuthSessionRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, auth_session: AuthSession) -> None:
        self.session.add(auth_session_to_orm(auth_session))

    def update(self, auth_session: AuthSession) -> None:
        obj = self.session.get(AuthSessionORM, auth_session.id)
        if obj is None:
            raise ValueError("Auth session not found.")
        obj.user_id = auth_session.user_id
        obj.session_revision = auth_session.session_revision
        obj.auth_method = auth_session.auth_method
        obj.device_label = auth_session.device_label
        obj.last_active_tenant_id = getattr(auth_session, "last_active_tenant_id", None)
        obj.last_active_organization_id = getattr(auth_session, "last_active_organization_id", None)
        obj.issued_at = auth_session.issued_at
        obj.expires_at = auth_session.expires_at
        obj.last_validated_at = auth_session.last_validated_at
        obj.revoked_at = auth_session.revoked_at
        obj.created_at = auth_session.created_at
        obj.updated_at = auth_session.updated_at

    def get(self, session_id: str) -> AuthSession | None:
        obj = self.session.get(AuthSessionORM, session_id)
        return auth_session_from_orm(obj) if obj else None

    def list_by_user(self, user_id: str) -> list[AuthSession]:
        stmt = select(AuthSessionORM).where(AuthSessionORM.user_id == user_id)
        rows = self.session.execute(stmt.order_by(AuthSessionORM.issued_at.desc())).scalars().all()
        return [auth_session_from_orm(row) for row in rows]

    def persist_context(
        self,
        session_id: str,
        *,
        last_active_tenant_id: str | None,
        last_active_organization_id: str | None,
        updated_at: datetime,
    ) -> bool:
        normalized_tenant_id = normalize_auth_session_context_id(last_active_tenant_id)
        normalized_organization_id = normalize_auth_session_context_id(last_active_organization_id)
        normalized_updated_at = normalize_auth_session_datetime(
            updated_at,
            code="AUTH_SESSION_TIMESTAMP_INVALID",
        )
        obj = self.session.get(AuthSessionORM, session_id)
        if obj is None:
            return False
        if (
            obj.last_active_tenant_id == normalized_tenant_id
            and obj.last_active_organization_id == normalized_organization_id
        ):
            return False
        obj.last_active_tenant_id = normalized_tenant_id
        obj.last_active_organization_id = normalized_organization_id
        obj.updated_at = normalized_updated_at
        return True

    def touch_validation(
        self,
        session_id: str,
        *,
        validated_at: datetime,
        throttle_seconds: int = 60,
    ) -> bool:
        min_elapsed_seconds = max(0, int(throttle_seconds or 0))
        obj = self.session.get(AuthSessionORM, session_id)
        if obj is None:
            return False
        current_validated_at = ensure_utc_datetime(obj.last_validated_at)
        normalized_validated_at = normalize_auth_session_datetime(
            validated_at,
            code="AUTH_SESSION_TIMESTAMP_INVALID",
        )
        if (
            current_validated_at is not None
            and min_elapsed_seconds > 0
            and (normalized_validated_at - current_validated_at).total_seconds() < min_elapsed_seconds
        ):
            return False
        obj.last_validated_at = normalized_validated_at
        obj.updated_at = normalized_validated_at
        self.session.flush()
        return True


class SqlAlchemyAuthPolicyReconciliationRepository(
    AuthPolicyReconciliationRepository
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, reconciliation: AuthPolicyReconciliation) -> None:
        self.session.add(
            AuthPolicyReconciliationORM(
                id=reconciliation.id,
                policy_name=reconciliation.policy_name,
                from_version=reconciliation.from_version,
                to_version=reconciliation.to_version,
                change_set_hash=reconciliation.change_set_hash,
                applied_at=reconciliation.applied_at,
                applied_by_user_id=reconciliation.applied_by_user_id,
                rollback_json=reconciliation.rollback_json,
            )
        )

    def get_latest(
        self,
        policy_name: str,
        *,
        for_update: bool = False,
    ) -> AuthPolicyReconciliation | None:
        stmt = (
            select(AuthPolicyReconciliationORM)
            .where(AuthPolicyReconciliationORM.policy_name == policy_name)
            .order_by(
                AuthPolicyReconciliationORM.to_version.desc(),
                AuthPolicyReconciliationORM.applied_at.desc(),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalars().first()
        if row is None:
            return None
        return AuthPolicyReconciliation(
            id=row.id,
            policy_name=row.policy_name,
            from_version=row.from_version,
            to_version=row.to_version,
            change_set_hash=row.change_set_hash,
            applied_at=ensure_utc_datetime(row.applied_at),
            applied_by_user_id=row.applied_by_user_id,
            rollback_json=row.rollback_json,
        )


class SqlAlchemyRoleRepository(RoleRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, role: Role) -> None:
        self.session.add(role_to_orm(role))

    def get(self, role_id: str) -> Role | None:
        obj = self.session.get(RoleORM, role_id)
        return role_from_orm(obj) if obj else None

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(RoleORM).where(
            RoleORM.name == str(name or "").strip().lower(),
            RoleORM.tenant_id.is_(None),
        )
        obj = self.session.execute(stmt).scalars().first()
        return role_from_orm(obj) if obj else None

    def get_for_tenant_by_name(
        self,
        tenant_id: str,
        name: str,
        *,
        include_system: bool = True,
    ) -> Role | None:
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_name = str(name or "").strip().lower()
        stmt = select(RoleORM).where(
            RoleORM.name == normalized_name,
            RoleORM.tenant_id == normalized_tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        if obj is not None or not include_system:
            return role_from_orm(obj) if obj is not None else None
        return self.get_by_name(normalized_name)

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        include_system: bool = True,
    ) -> list[Role]:
        normalized_tenant_id = str(tenant_id or "").strip()
        stmt = select(RoleORM)
        if include_system:
            stmt = stmt.where(
                or_(
                    RoleORM.tenant_id == normalized_tenant_id,
                    RoleORM.tenant_id.is_(None),
                )
            )
        else:
            stmt = stmt.where(RoleORM.tenant_id == normalized_tenant_id)
        rows = self.session.execute(
            stmt.order_by(RoleORM.name, RoleORM.tenant_id)
        ).scalars()
        return [role_from_orm(row) for row in rows]

    def update_custom(
        self,
        role: Role,
        *,
        expected_policy_version: int,
    ) -> bool:
        result = self.session.execute(
            update(RoleORM)
            .where(RoleORM.id == role.id)
            .where(RoleORM.tenant_id == role.tenant_id)
            .where(RoleORM.is_system.is_(False))
            .where(RoleORM.policy_version == expected_policy_version)
            .values(
                description=role.description,
                display_name=role.display_name,
                is_assignable=role.is_assignable,
                status=role.status,
                policy_version=role.policy_version,
                updated_at=role.updated_at,
            )
        )
        return bool(result.rowcount)

    def set_policy_version(
        self,
        role_id: str,
        *,
        policy_version: int,
        updated_at: datetime,
    ) -> bool:
        result = self.session.execute(
            update(RoleORM)
            .where(RoleORM.id == role_id)
            .values(
                policy_version=policy_version,
                updated_at=updated_at,
            )
        )
        return bool(result.rowcount)

    def list_all(self) -> list[Role]:
        rows = self.session.execute(select(RoleORM)).scalars().all()
        return [role_from_orm(row) for row in rows]


class SqlAlchemyRoleBindingRepository(RoleBindingRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, binding: RoleBinding) -> None:
        self.session.add(role_binding_to_orm(binding))

    def get(self, binding_id: str) -> RoleBinding | None:
        row = self.session.get(RoleBindingORM, binding_id)
        return role_binding_from_orm(row) if row is not None else None

    def list_active_for_principal(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
    ) -> list[RoleBinding]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.principal_id == principal_id)
            .where(RoleBindingORM.revoked_at.is_(None))
            .where(
                (RoleBindingORM.expires_at.is_(None))
                | (RoleBindingORM.expires_at > now)
            )
        )
        if tenant_id is None:
            stmt = stmt.where(RoleBindingORM.tenant_id.is_(None))
        else:
            stmt = stmt.where(RoleBindingORM.tenant_id == tenant_id)
        rows = self.session.execute(
            stmt.order_by(
                RoleBindingORM.actual_scope_type,
                RoleBindingORM.actual_scope_id,
                RoleBindingORM.role_id,
            )
        ).scalars()
        return [role_binding_from_orm(row) for row in rows]

    def list_active_for_role(
        self,
        role_id: str,
        *,
        tenant_id: str | None,
    ) -> list[RoleBinding]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.role_id == role_id)
            .where(RoleBindingORM.revoked_at.is_(None))
            .where(
                (RoleBindingORM.expires_at.is_(None))
                | (RoleBindingORM.expires_at > now)
            )
            .order_by(RoleBindingORM.principal_id)
        )
        if tenant_id is None:
            stmt = stmt.where(RoleBindingORM.tenant_id.is_(None))
        else:
            stmt = stmt.where(RoleBindingORM.tenant_id == tenant_id)
        rows = self.session.execute(stmt).scalars()
        return [role_binding_from_orm(row) for row in rows]

    def list_active_for_role_across_tenants(
        self,
        role_id: str,
    ) -> list[RoleBinding]:
        now = datetime.now(timezone.utc)
        rows = self.session.execute(
            select(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.role_id == role_id)
            .where(RoleBindingORM.tenant_id.is_not(None))
            .where(RoleBindingORM.revoked_at.is_(None))
            .where(
                (RoleBindingORM.expires_at.is_(None))
                | (RoleBindingORM.expires_at > now)
            )
            .order_by(
                RoleBindingORM.tenant_id,
                RoleBindingORM.principal_id,
            )
        ).scalars()
        return [role_binding_from_orm(row) for row in rows]

    def get_active_for_assignment(
        self,
        *,
        principal_id: str,
        role_id: str,
        tenant_id: str | None,
        actual_scope_type: str,
        actual_scope_id: str | None,
    ) -> RoleBinding | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.principal_id == principal_id)
            .where(RoleBindingORM.role_id == role_id)
            .where(RoleBindingORM.actual_scope_type == actual_scope_type)
            .where(RoleBindingORM.revoked_at.is_(None))
            .where(
                (RoleBindingORM.expires_at.is_(None))
                | (RoleBindingORM.expires_at > now)
            )
        )
        if tenant_id is None:
            stmt = stmt.where(RoleBindingORM.tenant_id.is_(None))
        else:
            stmt = stmt.where(RoleBindingORM.tenant_id == tenant_id)
        if actual_scope_id is None:
            stmt = stmt.where(RoleBindingORM.actual_scope_id.is_(None))
        else:
            stmt = stmt.where(
                RoleBindingORM.actual_scope_id == actual_scope_id
            )
        row = self.session.execute(stmt).scalars().first()
        return role_binding_from_orm(row) if row is not None else None

    def revoke_expired_for_assignment(
        self,
        *,
        principal_id: str,
        role_id: str,
        tenant_id: str | None,
        actual_scope_type: str,
        actual_scope_id: str | None,
        as_of: datetime,
    ) -> int:
        stmt = (
            update(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.principal_id == principal_id)
            .where(RoleBindingORM.role_id == role_id)
            .where(RoleBindingORM.actual_scope_type == actual_scope_type)
            .where(RoleBindingORM.revoked_at.is_(None))
            .where(RoleBindingORM.expires_at.is_not(None))
            .where(RoleBindingORM.expires_at <= as_of)
        )
        if tenant_id is None:
            stmt = stmt.where(RoleBindingORM.tenant_id.is_(None))
        else:
            stmt = stmt.where(RoleBindingORM.tenant_id == tenant_id)
        if actual_scope_id is None:
            stmt = stmt.where(RoleBindingORM.actual_scope_id.is_(None))
        else:
            stmt = stmt.where(
                RoleBindingORM.actual_scope_id == actual_scope_id
            )
        result = self.session.execute(
            stmt.values(
                revoked_at=as_of,
                version=RoleBindingORM.version + 1,
            )
        )
        return int(result.rowcount or 0)

    def revoke(self, binding_id: str, *, revoked_at: datetime) -> bool:
        result = self.session.execute(
            update(RoleBindingORM)
            .where(RoleBindingORM.id == binding_id)
            .where(RoleBindingORM.revoked_at.is_(None))
            .values(
                revoked_at=revoked_at,
                version=RoleBindingORM.version + 1,
            )
        )
        return bool(result.rowcount)

    def revoke_active_for_principal_tenant(
        self,
        principal_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int:
        result = self.session.execute(
            update(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.principal_id == principal_id)
            .where(RoleBindingORM.tenant_id == tenant_id)
            .where(RoleBindingORM.revoked_at.is_(None))
            .values(
                revoked_at=revoked_at,
                version=RoleBindingORM.version + 1,
            )
        )
        return int(result.rowcount or 0)

    def revoke_active_for_role(
        self,
        role_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int:
        result = self.session.execute(
            update(RoleBindingORM)
            .where(RoleBindingORM.principal_type == "user")
            .where(RoleBindingORM.role_id == role_id)
            .where(RoleBindingORM.tenant_id == tenant_id)
            .where(RoleBindingORM.revoked_at.is_(None))
            .values(
                revoked_at=revoked_at,
                version=RoleBindingORM.version + 1,
            )
        )
        return int(result.rowcount or 0)


class SqlAlchemyRoleDelegationPolicyRepository(
    RoleDelegationPolicyRepository
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, policy: RoleDelegationPolicy) -> None:
        self.session.add(role_delegation_policy_to_orm(policy))

    def get(self, policy_id: str) -> RoleDelegationPolicy | None:
        row = self.session.get(RoleDelegationPolicyORM, policy_id)
        return (
            role_delegation_policy_from_orm(row)
            if row is not None
            else None
        )

    def get_active_exact(
        self,
        *,
        actor_role_id: str,
        assignable_role_id: str,
        tenant_id: str | None,
        target_scope_type: str,
    ) -> RoleDelegationPolicy | None:
        stmt = (
            select(RoleDelegationPolicyORM)
            .where(
                RoleDelegationPolicyORM.actor_role_id == actor_role_id
            )
            .where(
                RoleDelegationPolicyORM.assignable_role_id
                == assignable_role_id
            )
            .where(
                RoleDelegationPolicyORM.target_scope_type
                == target_scope_type
            )
            .where(RoleDelegationPolicyORM.revoked_at.is_(None))
        )
        if tenant_id is None:
            stmt = stmt.where(
                RoleDelegationPolicyORM.tenant_id.is_(None)
            )
        else:
            stmt = stmt.where(
                RoleDelegationPolicyORM.tenant_id == tenant_id
            )
        row = self.session.execute(stmt).scalars().first()
        return (
            role_delegation_policy_from_orm(row)
            if row is not None
            else None
        )

    def find_active(
        self,
        *,
        actor_role_ids: set[str],
        assignable_role_id: str,
        tenant_id: str,
        target_scope_type: str,
    ) -> RoleDelegationPolicy | None:
        if not actor_role_ids:
            return None
        base_stmt = (
            select(RoleDelegationPolicyORM)
            .where(
                RoleDelegationPolicyORM.actor_role_id.in_(
                    sorted(actor_role_ids)
                )
            )
            .where(
                RoleDelegationPolicyORM.assignable_role_id
                == assignable_role_id
            )
            .where(
                RoleDelegationPolicyORM.target_scope_type
                == target_scope_type
            )
            .where(RoleDelegationPolicyORM.revoked_at.is_(None))
        )
        tenant_stmt = base_stmt.where(
            RoleDelegationPolicyORM.tenant_id == tenant_id
        )
        row = self.session.execute(tenant_stmt).scalars().first()
        if row is None:
            system_stmt = base_stmt.where(
                RoleDelegationPolicyORM.tenant_id.is_(None)
            )
            row = self.session.execute(system_stmt).scalars().first()
        return (
            role_delegation_policy_from_orm(row)
            if row is not None
            else None
        )

    def revoke(self, policy_id: str, *, revoked_at: datetime) -> bool:
        result = self.session.execute(
            update(RoleDelegationPolicyORM)
            .where(RoleDelegationPolicyORM.id == policy_id)
            .where(RoleDelegationPolicyORM.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        return bool(result.rowcount)


class SqlAlchemyPermissionRepository(PermissionRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, permission: Permission) -> None:
        self.session.add(permission_to_orm(permission))

    def get(self, permission_id: str) -> Permission | None:
        obj = self.session.get(PermissionORM, permission_id)
        return permission_from_orm(obj) if obj else None

    def get_by_code(self, code: str) -> Permission | None:
        stmt = select(PermissionORM).where(PermissionORM.code == code)
        obj = self.session.execute(stmt).scalars().first()
        return permission_from_orm(obj) if obj else None

    def list_all(self) -> list[Permission]:
        rows = self.session.execute(select(PermissionORM)).scalars().all()
        return [permission_from_orm(row) for row in rows]


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, binding: RolePermissionBinding) -> None:
        if self.exists(binding.role_id, binding.permission_id):
            return
        self.session.add(role_permission_to_orm(binding))

    def delete(self, role_id: str, permission_id: str) -> None:
        self.session.query(RolePermissionORM).filter_by(
            role_id=role_id,
            permission_id=permission_id,
        ).delete()

    def exists(self, role_id: str, permission_id: str) -> bool:
        stmt = select(RolePermissionORM.id).where(
            RolePermissionORM.role_id == role_id,
            RolePermissionORM.permission_id == permission_id,
        )
        return self.session.execute(stmt).first() is not None

    def list_permission_ids(self, role_id: str) -> list[str]:
        stmt = select(RolePermissionORM.permission_id).where(RolePermissionORM.role_id == role_id)
        return list(self.session.execute(stmt).scalars().all())


__all__ = [
    "SqlAlchemyAuthPolicyReconciliationRepository",
    "SqlAlchemyAuthSessionRepository",
    "SqlAlchemyUserRepository",
    "SqlAlchemyRoleRepository",
    "SqlAlchemyPermissionRepository",
    "SqlAlchemyRoleBindingRepository",
    "SqlAlchemyRoleDelegationPolicyRepository",
    "SqlAlchemyRolePermissionRepository",
]
