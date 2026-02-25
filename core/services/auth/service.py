from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import NotFoundError, ValidationError
from core.interfaces import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from core.models import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from core.services.auth.authorization import require_permission
from core.services.auth.passwords import hash_password, verify_password
from core.services.auth.policy import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from core.services.auth.session import UserSessionContext, UserSessionPrincipal

if TYPE_CHECKING:
    from core.services.audit.service import AuditService


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        session: Session,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        user_role_repo: UserRoleRepository,
        role_permission_repo: RolePermissionRepository,
        user_session: UserSessionContext | None = None,
        audit_service: "AuditService | None" = None,
    ):
        self._session: Session = session
        self._user_repo: UserRepository = user_repo
        self._role_repo: RoleRepository = role_repo
        self._permission_repo: PermissionRepository = permission_repo
        self._user_role_repo: UserRoleRepository = user_role_repo
        self._role_permission_repo: RolePermissionRepository = role_permission_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service

    def bootstrap_defaults(self) -> UserAccount:
        self._ensure_default_permissions()
        self._session.flush()
        role_map = self._ensure_default_roles()
        self._session.flush()
        self._ensure_role_permissions(role_map)
        self._session.flush()

        admin_username = (os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin").lower()
        admin_password = os.getenv("PM_ADMIN_PASSWORD", "ChangeMe123!")
        admin = self._user_repo.get_by_username(admin_username)
        if admin is None:
            admin = self.register_user(
                username=admin_username,
                raw_password=admin_password,
                display_name="Administrator",
                role_names=["admin"],
                commit=False,
                bypass_permission=True,
            )
        else:
            admin_role = role_map.get("admin")
            if admin_role and not self._user_role_repo.exists(admin.id, admin_role.id):
                self._user_role_repo.add(UserRoleBinding.create(user_id=admin.id, role_id=admin_role.id))

        self._session.commit()
        return admin

    def register_user(
        self,
        username: str,
        raw_password: str,
        display_name: str | None = None,
        email: str | None = None,
        is_active: bool = True,
        role_names: Iterable[str] | None = None,
        *,
        commit: bool = True,
        bypass_permission: bool = False,
    ) -> UserAccount:
        if not bypass_permission:
            require_permission(self._user_session, "auth.manage", operation_label="register user")
        normalized = (username or "").strip().lower()
        normalized_email = self._normalize_email(email)
        if not normalized:
            raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
        self._validate_email(normalized_email)
        self._validate_password(raw_password)
        if self._user_repo.get_by_username(normalized):
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")

        user = UserAccount.create(
            username=normalized,
            password_hash=hash_password(raw_password),
            display_name=(display_name or "").strip() or None,
            email=normalized_email,
            is_active=is_active,
        )
        try:
            with self._session.begin_nested():
                self._user_repo.add(user)
                self._assign_roles_for_user(user.id, role_names or ("viewer",))
            if commit:
                self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if "username" in str(exc).lower():
                raise ValidationError(
                    "Username already exists.",
                    code="USERNAME_EXISTS",
                ) from exc
            raise ValidationError(
                "Failed to create user due to data conflict.",
                code="USER_CREATE_CONFLICT",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        return user

    def authenticate(self, username: str, raw_password: str) -> UserAccount:
        normalized = (username or "").strip().lower()
        user = self._user_repo.get_by_username(normalized)
        if not user or not user.is_active:
            self._record_auth_event(
                action="auth.login.failed",
                username=normalized,
                user_id=user.id if user else None,
                details={"reason": "invalid_credentials"},
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if not verify_password(raw_password, user.password_hash):
            self._record_auth_event(
                action="auth.login.failed",
                username=normalized,
                user_id=user.id,
                details={"reason": "invalid_credentials"},
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        self._record_auth_event(
            action="auth.login.success",
            username=user.username,
            user_id=user.id,
            details={"result": "ok"},
        )
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = self._require_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")

        self._validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()

    def reset_user_password(self, user_id: str, new_password: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="reset user password")
        user = self._require_user(user_id)
        self._validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()

    def assign_role(self, user_id: str, role_name: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="assign role")
        user = self._require_user(user_id)
        role = self._require_role_by_name(role_name)
        if not self._user_role_repo.exists(user.id, role.id):
            self._user_role_repo.add(UserRoleBinding.create(user_id=user.id, role_id=role.id))
            self._session.commit()

    def revoke_role(self, user_id: str, role_name: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="revoke role")
        user = self._require_user(user_id)
        role = self._require_role_by_name(role_name)
        self._user_role_repo.delete(user.id, role.id)
        self._session.commit()

    def get_user_permissions(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        role_ids = self._user_role_repo.list_role_ids(user_id)
        permission_ids: set[str] = set()
        for role_id in role_ids:
            permission_ids.update(self._role_permission_repo.list_permission_ids(role_id))

        all_permissions = {perm.id: perm.code for perm in self._permission_repo.list_all()}
        return {all_permissions[pid] for pid in permission_ids if pid in all_permissions}

    def has_permission(self, user_id: str, permission_code: str) -> bool:
        return permission_code in self.get_user_permissions(user_id)

    def list_users(self) -> list[UserAccount]:
        require_permission(self._user_session, "auth.manage", operation_label="list users")
        return self._user_repo.list_all()

    def list_roles(self) -> list[Role]:
        require_permission(self._user_session, "auth.manage", operation_label="list roles")
        return self._role_repo.list_all()

    def set_user_active(self, user_id: str, is_active: bool) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="set user active")
        user = self._require_user(user_id)
        user.is_active = bool(is_active)
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        return user

    def update_user_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="update user profile")
        user = self._require_user(user_id)

        if username is not None:
            normalized = (username or "").strip().lower()
            if not normalized:
                raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
            existing = self._user_repo.get_by_username(normalized)
            if existing and existing.id != user.id:
                raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
            user.username = normalized

        if display_name is not None:
            user.display_name = (display_name or "").strip() or None

        if email is not None:
            normalized_email = self._normalize_email(email)
            self._validate_email(normalized_email)
            user.email = normalized_email

        user.updated_at = datetime.now(timezone.utc)
        try:
            self._user_repo.update(user)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if "username" in str(exc).lower():
                raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
            raise ValidationError(
                "Failed to update user due to data conflict.",
                code="USER_UPDATE_CONFLICT",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        return user

    def get_user_role_names(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        role_ids = self._user_role_repo.list_role_ids(user_id)
        names: set[str] = set()
        for role_id in role_ids:
            role = self._role_repo.get(role_id)
            if role:
                names.add(role.name)
        return names

    def build_principal(self, user: UserAccount) -> UserSessionPrincipal:
        return UserSessionPrincipal(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role_names=frozenset(self.get_user_role_names(user.id)),
            permissions=frozenset(self.get_user_permissions(user.id)),
        )

    def _assign_roles_for_user(self, user_id: str, role_names: Iterable[str]) -> None:
        for role_name in role_names:
            role = self._require_role_by_name(role_name)
            if not self._user_role_repo.exists(user_id, role.id):
                self._user_role_repo.add(UserRoleBinding.create(user_id=user_id, role_id=role.id))

    def _ensure_default_permissions(self) -> None:
        for code, description in DEFAULT_PERMISSIONS.items():
            if self._permission_repo.get_by_code(code) is None:
                self._permission_repo.add(Permission.create(code=code, description=description))

    def _ensure_default_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            role = self._role_repo.get_by_name(role_name)
            if role is None:
                role = Role.create(name=role_name, description=f"System role: {role_name}", is_system=True)
                self._role_repo.add(role)
            roles[role_name] = role
        return roles

    def _ensure_role_permissions(self, role_map: dict[str, Role]) -> None:
        permission_map = {p.code: p.id for p in self._permission_repo.list_all()}
        for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = role_map.get(role_name)
            if not role:
                continue
            for code in permission_codes:
                permission_id = permission_map.get(code)
                if not permission_id:
                    continue
                if not self._role_permission_repo.exists(role.id, permission_id):
                    self._role_permission_repo.add(
                        RolePermissionBinding.create(
                            role_id=role.id,
                            permission_id=permission_id,
                        )
                    )

    def _require_role_by_name(self, role_name: str) -> Role:
        role = self._role_repo.get_by_name((role_name or "").strip().lower())
        if not role:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_user(self, user_id: str) -> UserAccount:
        user = self._user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    @staticmethod
    def _validate_password(password: str) -> None:
        pwd = password or ""
        if len(pwd) < 8:
            raise ValidationError(
                "Password must be at least 8 characters.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.islower() for ch in pwd):
            raise ValidationError(
                "Password must include a lowercase letter.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.isupper() for ch in pwd):
            raise ValidationError(
                "Password must include an uppercase letter.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.isdigit() for ch in pwd):
            raise ValidationError(
                "Password must include a digit.",
                code="WEAK_PASSWORD",
            )

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        value = (email or "").strip().lower()
        return value or None

    @staticmethod
    def _validate_email(email: str | None) -> None:
        if email is None:
            return
        if not _EMAIL_RE.match(email):
            raise ValidationError(
                "Invalid email format.",
                code="INVALID_EMAIL",
            )

    def _record_auth_event(
        self,
        *,
        action: str,
        username: str,
        user_id: str | None,
        details: dict[str, str],
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.record(
                action=action,
                entity_type="auth_session",
                entity_id=user_id or username or "unknown",
                actor_user_id=user_id,
                actor_username=username or None,
                details=details,
                commit=True,
            )
        except Exception as exc:
            logger.warning("Failed to write auth audit event '%s': %s", action, exc)


__all__ = ["AuthService"]
