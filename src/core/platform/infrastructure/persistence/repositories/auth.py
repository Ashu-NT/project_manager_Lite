from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.domain import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
)
from src.core.platform.infrastructure.persistence.mappers.auth import (
    auth_session_from_orm,
    auth_session_to_orm,
    permission_from_orm,
    permission_to_orm,
    role_from_orm,
    role_permission_to_orm,
    role_to_orm,
    user_from_orm,
    user_role_to_orm,
    user_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.auth import AuthSessionORM, PermissionORM, RoleORM, RolePermissionORM, UserORM, UserRoleORM
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
        bind = self.session.get_bind()
        normalized_tenant_id = str(last_active_tenant_id or "").strip() or None
        normalized_organization_id = str(last_active_organization_id or "").strip() or None
        normalized_updated_at = ensure_utc_datetime(updated_at)
        with Session(bind=bind) as temp_session:
            obj = temp_session.get(AuthSessionORM, session_id)
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
            temp_session.commit()
            return True

    def touch_validation(
        self,
        session_id: str,
        *,
        validated_at: datetime,
        throttle_seconds: int = 60,
    ) -> bool:
        bind = self.session.get_bind()
        min_elapsed_seconds = max(0, int(throttle_seconds or 0))
        with Session(bind=bind) as temp_session:
            obj = temp_session.get(AuthSessionORM, session_id)
            if obj is None:
                return False
            current_validated_at = ensure_utc_datetime(obj.last_validated_at)
            if (
                current_validated_at is not None
                and min_elapsed_seconds > 0
                and (validated_at - current_validated_at).total_seconds() < min_elapsed_seconds
            ):
                return False
            obj.last_validated_at = validated_at
            obj.updated_at = validated_at
            temp_session.commit()
            return True


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
        stmt = select(RoleORM).where(RoleORM.name == name)
        obj = self.session.execute(stmt).scalars().first()
        return role_from_orm(obj) if obj else None

    def list_all(self) -> list[Role]:
        rows = self.session.execute(select(RoleORM)).scalars().all()
        return [role_from_orm(row) for row in rows]


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


class SqlAlchemyUserRoleRepository(UserRoleRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, binding: UserRoleBinding) -> None:
        if self.exists(binding.user_id, binding.role_id, organization_id=binding.organization_id):
            return
        self.session.add(user_role_to_orm(binding))

    def delete(self, user_id: str, role_id: str, organization_id: str | None = None) -> None:
        stmt = (
            self.session.query(UserRoleORM)
            .filter_by(user_id=user_id, role_id=role_id)
        )
        if organization_id is None:
            stmt = stmt.filter(UserRoleORM.organization_id.is_(None))
        else:
            stmt = stmt.filter(UserRoleORM.organization_id == organization_id)
        stmt.delete()

    def exists(self, user_id: str, role_id: str, organization_id: str | None = None) -> bool:
        stmt = select(UserRoleORM.id).where(
            UserRoleORM.user_id == user_id,
            UserRoleORM.role_id == role_id,
        )
        if organization_id is None:
            stmt = stmt.where(UserRoleORM.organization_id.is_(None))
        else:
            stmt = stmt.where(UserRoleORM.organization_id == organization_id)
        return self.session.execute(stmt).first() is not None

    def list_role_ids(self, user_id: str) -> list[str]:
        stmt = select(UserRoleORM.role_id).where(
            UserRoleORM.user_id == user_id,
            UserRoleORM.organization_id.is_(None),
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_role_ids_for_organization(self, user_id: str, organization_id: str) -> list[str]:
        stmt = select(UserRoleORM.role_id).where(
            UserRoleORM.user_id == user_id,
            UserRoleORM.organization_id == organization_id,
        )
        return list(self.session.execute(stmt).scalars().all())


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
    "SqlAlchemyAuthSessionRepository",
    "SqlAlchemyUserRepository",
    "SqlAlchemyRoleRepository",
    "SqlAlchemyPermissionRepository",
    "SqlAlchemyUserRoleRepository",
    "SqlAlchemyRolePermissionRepository",
]
