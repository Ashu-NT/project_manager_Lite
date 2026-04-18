from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import ValidationError
from src.core.platform.access.contracts import (
    ProjectMembershipRepository,
    ScopedAccessGrantRepository,
)
from src.core.platform.auth.application.auth_query import AuthQueryMixin
from src.core.platform.auth.application.auth_validation import AuthValidationMixin
from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
)
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.auth.mfa import generate_mfa_secret, verify_totp_code
from src.core.platform.auth.passwords import hash_password, verify_password
from src.core.platform.auth.policy import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    login_lockout_minutes,
    login_lockout_threshold,
    session_timeout_minutes,
)
from src.core.platform.auth.sod import SeparationOfDutiesPolicy, find_separation_of_duties_conflicts

if TYPE_CHECKING:
    from core.platform.audit.service import AuditService


logger = logging.getLogger(__name__)


class AuthService(AuthQueryMixin, AuthValidationMixin):
    def __init__(
        self,
        session: Session,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        user_role_repo: UserRoleRepository,
        role_permission_repo: RolePermissionRepository,
        auth_session_repo: AuthSessionRepository | None = None,
        scoped_access_repo: ScopedAccessGrantRepository | None = None,
        project_membership_repo: ProjectMembershipRepository | None = None,
        user_session: UserSessionContext | None = None,
        audit_service: "AuditService | None" = None,
        sod_policy: SeparationOfDutiesPolicy | None = None,
    ):
        self._session: Session = session
        self._user_repo: UserRepository = user_repo
        self._role_repo: RoleRepository = role_repo
        self._permission_repo: PermissionRepository = permission_repo
        self._user_role_repo: UserRoleRepository = user_role_repo
        self._role_permission_repo: RolePermissionRepository = role_permission_repo
        self._auth_session_repo: AuthSessionRepository | None = auth_session_repo
        self._scoped_access_repo: ScopedAccessGrantRepository | None = scoped_access_repo
        self._project_membership_repo: ProjectMembershipRepository | None = project_membership_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._sod_policy = sod_policy or SeparationOfDutiesPolicy()

    def bootstrap_defaults(self) -> UserAccount:
        self._ensure_default_permissions()
        self._session.flush()
        role_map = self._ensure_default_roles()
        self._session.flush()
        self._ensure_role_permissions(role_map)
        self._session.flush()

        admin_username = (os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin").lower()
        admin = self._user_repo.get_by_username(admin_username)
        if admin is None:
            admin_password = self._resolve_bootstrap_admin_password()
            admin = self.register_user(
                username=admin_username,
                raw_password=admin_password,
                display_name="Administrator",
                role_names=["admin"],
                must_change_password=True,
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
        must_change_password: bool = False,
        *,
        identity_provider: str | None = None,
        federated_subject: str | None = None,
        session_timeout_minutes_override: int | None = None,
        commit: bool = True,
        bypass_permission: bool = False,
    ) -> UserAccount:
        if not bypass_permission:
            require_permission(self._user_session, "auth.manage", operation_label="register user")
        normalized = (username or "").strip().lower()
        normalized_email = self._normalize_email(email)
        normalized_identity_provider = self._normalize_identity_provider(identity_provider)
        normalized_federated_subject = self._normalize_federated_subject(federated_subject)
        if not normalized:
            raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
        self._validate_email(normalized_email)
        self._validate_password(raw_password)
        self._validate_federated_identity(normalized_identity_provider, normalized_federated_subject)
        resolved_session_timeout = self._validate_session_timeout_override(session_timeout_minutes_override)
        if self._user_repo.get_by_username(normalized):
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
        if normalized_identity_provider and normalized_federated_subject:
            if self._user_repo.get_by_federated_identity(normalized_identity_provider, normalized_federated_subject):
                raise ValidationError(
                    "Federated identity is already linked to another user.",
                    code="FEDERATED_IDENTITY_EXISTS",
                )

        resolved_role_names = tuple(role_names or ("viewer",))
        self._enforce_separation_of_duties(resolved_role_names)

        user = UserAccount.create(
            username=normalized,
            password_hash=hash_password(raw_password),
            display_name=(display_name or "").strip() or None,
            email=normalized_email,
            is_active=is_active,
        )
        user.must_change_password = bool(must_change_password)
        user.identity_provider = normalized_identity_provider
        user.federated_subject = normalized_federated_subject
        user.session_timeout_minutes_override = resolved_session_timeout
        try:
            with self._session.begin_nested():
                self._user_repo.add(user)
                self._assign_roles_for_user(user.id, resolved_role_names)
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
        domain_events.auth_changed.emit(user.id)
        return user

    def authenticate(
        self,
        username: str,
        raw_password: str,
        *,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        normalized = (username or "").strip().lower()
        now = datetime.now(timezone.utc)
        user = self._user_repo.get_by_username(normalized)
        if not user or not user.is_active:
            self._record_auth_event(
                action="auth.login.failed",
                username=normalized,
                user_id=user.id if user else None,
                details={"reason": "invalid_credentials"},
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = now
            self._user_repo.update(user)
            self._session.commit()
            domain_events.auth_changed.emit(user.id)
        if user.locked_until is not None and user.locked_until > now:
            self._record_auth_event(
                action="auth.login.failed",
                username=normalized,
                user_id=user.id,
                details={
                    "reason": "locked_out",
                    "locked_until": user.locked_until.isoformat(),
                },
            )
            raise ValidationError(
                f"Account is locked until {user.locked_until.isoformat()}.",
                code="AUTH_LOCKED",
            )
        if not verify_password(raw_password, user.password_hash):
            self._register_failed_login(user, username=normalized, occurred_at=now)
            self._record_auth_event(
                action="auth.login.failed",
                username=normalized,
                user_id=user.id,
                details={
                    "reason": "invalid_credentials",
                    "failed_attempts": str(user.failed_login_attempts),
                    "locked_until": user.locked_until.isoformat() if user.locked_until else "",
                },
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if bool(getattr(user, "mfa_enabled", False)):
            if not verify_totp_code(getattr(user, "mfa_secret", None), mfa_code, at_time=now):
                self._register_failed_login(user, username=normalized, occurred_at=now)
                reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
                self._record_auth_event(
                    action="auth.login.failed",
                    username=normalized,
                    user_id=user.id,
                    details={"reason": reason},
                )
                message = (
                    "Multi-factor authentication code is required."
                    if reason == "mfa_required"
                    else "Invalid multi-factor authentication code."
                )
                code = "AUTH_MFA_REQUIRED" if reason == "mfa_required" else "AUTH_MFA_FAILED"
                raise ValidationError(message, code=code)
        self._complete_successful_authentication(
            user,
            occurred_at=now,
            auth_method="password",
            device_label=device_label,
        )
        return user

    def authenticate_federated(
        self,
        *,
        identity_provider: str,
        federated_subject: str,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        normalized_identity_provider = self._normalize_identity_provider(identity_provider)
        normalized_federated_subject = self._normalize_federated_subject(federated_subject)
        self._validate_federated_identity(normalized_identity_provider, normalized_federated_subject)
        now = datetime.now(timezone.utc)
        user = self._user_repo.get_by_federated_identity(
            normalized_identity_provider,
            normalized_federated_subject,
        )
        audit_username = f"{normalized_identity_provider}:{normalized_federated_subject}"
        if not user or not user.is_active:
            self._record_auth_event(
                action="auth.login.failed",
                username=audit_username,
                user_id=user.id if user else None,
                details={"reason": "invalid_federated_identity"},
            )
            raise ValidationError("Invalid federated identity.", code="AUTH_FAILED")
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = now
            self._user_repo.update(user)
            self._session.commit()
            domain_events.auth_changed.emit(user.id)
        if user.locked_until is not None and user.locked_until > now:
            self._record_auth_event(
                action="auth.login.failed",
                username=audit_username,
                user_id=user.id,
                details={
                    "reason": "locked_out",
                    "locked_until": user.locked_until.isoformat(),
                },
            )
            raise ValidationError(
                f"Account is locked until {user.locked_until.isoformat()}.",
                code="AUTH_LOCKED",
            )
        if bool(getattr(user, "mfa_enabled", False)):
            if not verify_totp_code(getattr(user, "mfa_secret", None), mfa_code, at_time=now):
                self._register_failed_login(user, username=user.username, occurred_at=now)
                reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
                self._record_auth_event(
                    action="auth.login.failed",
                    username=audit_username,
                    user_id=user.id,
                    details={"reason": reason},
                )
                message = (
                    "Multi-factor authentication code is required."
                    if reason == "mfa_required"
                    else "Invalid multi-factor authentication code."
                )
                code = "AUTH_MFA_REQUIRED" if reason == "mfa_required" else "AUTH_MFA_FAILED"
                raise ValidationError(message, code=code)
        self._complete_successful_authentication(
            user,
            occurred_at=now,
            auth_method=f"federated:{normalized_identity_provider}",
            device_label=device_label,
        )
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = self._require_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")

        self._validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        user.password_changed_at = user.updated_at
        user.must_change_password = False
        self._rotate_session_revision(user)
        user.session_expires_at = self._next_session_expiry(user.updated_at, user=user)
        self._revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)

    def reset_user_password(self, user_id: str, new_password: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="reset user password")
        user = self._require_user(user_id)
        self._validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        user.password_changed_at = user.updated_at
        user.must_change_password = True
        self._rotate_session_revision(user)
        user.session_expires_at = self._next_session_expiry(user.updated_at, user=user)
        self._revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)

    def assign_role(self, user_id: str, role_name: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="assign role")
        user = self._require_user(user_id)
        existing_role_names = self.get_user_role_names(user.id)
        self._enforce_separation_of_duties(tuple(existing_role_names) + (role_name,))
        role = self._require_role_by_name(role_name)
        if not self._user_role_repo.exists(user.id, role.id):
            self._user_role_repo.add(UserRoleBinding.create(user_id=user.id, role_id=role.id))
            self._session.commit()
            domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)

    def revoke_role(self, user_id: str, role_name: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="revoke role")
        user = self._require_user(user_id)
        role = self._require_role_by_name(role_name)
        self._user_role_repo.delete(user.id, role.id)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)

    def list_users(self) -> list[UserAccount]:
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read", "access.manage", "security.manage"),
            operation_label="list users",
        )
        return self._user_repo.list_all()

    def list_roles(self) -> list[Role]:
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read"),
            operation_label="list roles",
        )
        return self._role_repo.list_all()

    def set_user_active(self, user_id: str, is_active: bool) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="set user active")
        user = self._require_user(user_id)
        user.is_active = bool(is_active)
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
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
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def unlock_user_account(self, user_id: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="unlock user account",
        )
        user = self._require_user(user_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def link_federated_identity(
        self,
        user_id: str,
        *,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="link federated identity",
        )
        user = self._require_user(user_id)
        normalized_identity_provider = self._normalize_identity_provider(identity_provider)
        normalized_federated_subject = self._normalize_federated_subject(federated_subject)
        self._validate_federated_identity(normalized_identity_provider, normalized_federated_subject)
        existing = self._user_repo.get_by_federated_identity(
            normalized_identity_provider,
            normalized_federated_subject,
        )
        if existing is not None and existing.id != user.id:
            raise ValidationError(
                "Federated identity is already linked to another user.",
                code="FEDERATED_IDENTITY_EXISTS",
            )
        user.identity_provider = normalized_identity_provider
        user.federated_subject = normalized_federated_subject
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def provision_mfa_secret(self, user_id: str) -> str:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="provision user mfa secret",
        )
        user = self._require_user(user_id)
        user.mfa_secret = generate_mfa_secret()
        user.mfa_enabled = False
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return str(user.mfa_secret or "")

    def enable_user_mfa(self, user_id: str, verification_code: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="enable user mfa",
        )
        user = self._require_user(user_id)
        if not verify_totp_code(getattr(user, "mfa_secret", None), verification_code):
            raise ValidationError(
                "Invalid multi-factor authentication verification code.",
                code="AUTH_MFA_FAILED",
            )
        user.mfa_enabled = True
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def disable_user_mfa(self, user_id: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="disable user mfa",
        )
        user = self._require_user(user_id)
        user.mfa_enabled = False
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def set_user_session_policy(
        self,
        user_id: str,
        *,
        session_timeout_minutes_override: int | None,
    ) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="set user session policy",
        )
        user = self._require_user(user_id)
        user.session_timeout_minutes_override = self._validate_session_timeout_override(
            session_timeout_minutes_override
        )
        user.updated_at = datetime.now(timezone.utc)
        self._rotate_session_revision(user)
        user.session_expires_at = self._next_session_expiry(user.updated_at, user=user)
        self._revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._refresh_current_session_if_user(user.id)
        return user

    def revoke_user_sessions(self, user_id: str, *, note: str = "") -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="revoke user sessions",
        )
        user = self._require_user(user_id)
        self._rotate_session_revision(user)
        user.session_expires_at = datetime.now(timezone.utc)
        user.updated_at = user.session_expires_at
        self._revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._record_auth_event(
            action="auth.session.revoked",
            username=user.username,
            user_id=user.id,
            details={"note": note.strip()},
        )
        self._refresh_current_session_if_user(user.id)
        return user

    def list_user_sessions(self, user_id: str) -> list[AuthSession]:
        require_any_permission(
            self._user_session,
            ("auth.read", "auth.manage", "security.manage"),
            operation_label="list user sessions",
        )
        user = self._require_user(user_id)
        if self._auth_session_repo is None:
            return []
        return self._auth_session_repo.list_by_user(user.id)

    def revoke_session(self, session_id: str, *, note: str = "") -> AuthSession:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="revoke session",
        )
        if self._auth_session_repo is None:
            raise ValidationError(
                "Session persistence is not configured.",
                code="AUTH_SESSION_PERSISTENCE_REQUIRED",
            )
        auth_session = self._auth_session_repo.get(session_id)
        if auth_session is None:
            raise ValidationError("Session not found.", code="AUTH_SESSION_NOT_FOUND")
        revoked_at = datetime.now(timezone.utc)
        auth_session.revoked_at = revoked_at
        auth_session.updated_at = revoked_at
        self._auth_session_repo.update(auth_session)
        self._session.commit()
        self._record_auth_event(
            action="auth.session.revoked",
            username="",
            user_id=auth_session.user_id,
            details={"note": note.strip(), "session_id": auth_session.id},
        )
        self._refresh_current_session_if_user(auth_session.user_id)
        return auth_session

    def validate_session_principal(self, principal: UserSessionPrincipal) -> UserSessionPrincipal | None:
        user = self._user_repo.get(principal.user_id)
        if user is None or not user.is_active:
            return None
        now = datetime.now(timezone.utc)
        current_expires_at = ensure_utc_datetime(user.session_expires_at)
        if current_expires_at is None or now >= current_expires_at:
            return None
        principal_expires_at = ensure_utc_datetime(principal.session_expires_at)
        if self._auth_session_repo is not None and getattr(principal, "session_id", None):
            auth_session = self._auth_session_repo.get(principal.session_id)
            if auth_session is None or auth_session.user_id != user.id:
                return None
            if auth_session.revoked_at is not None:
                return None
            if auth_session.expires_at is None or now >= ensure_utc_datetime(auth_session.expires_at):
                return None
            if int(auth_session.session_revision or 1) != int(getattr(user, "session_revision", 1) or 1):
                return None
            if principal_expires_at is None or principal_expires_at != ensure_utc_datetime(auth_session.expires_at):
                return self.build_principal(user, session_id=auth_session.id)
            return self.build_principal(user, session_id=auth_session.id)
        if principal_expires_at is None or principal_expires_at != current_expires_at:
            return None
        if int(getattr(principal, "session_revision", 1) or 1) != int(getattr(user, "session_revision", 1) or 1):
            return None
        return self.build_principal(user)

    def build_principal(self, user: UserAccount, *, session_id: str | None = None) -> UserSessionPrincipal:
        scoped_access: dict[str, dict[str, frozenset[str]]] = {}
        if self._scoped_access_repo is not None:
            for grant in self._scoped_access_repo.list_by_user(user.id):
                scope_type = str(grant.scope_type or "").strip().lower()
                scope_id = str(grant.scope_id or "").strip()
                if not scope_type or not scope_id:
                    continue
                permissions = frozenset(
                    str(code).strip()
                    for code in grant.permission_codes
                    if str(code).strip()
                )
                if not permissions:
                    continue
                scope_rows = scoped_access.setdefault(scope_type, {})
                existing_permissions = scope_rows.get(scope_id, frozenset())
                scope_rows[scope_id] = frozenset(set(existing_permissions).union(permissions))
        elif self._project_membership_repo is not None:
            scoped_access["project"] = {}
            for membership in self._project_membership_repo.list_by_user(user.id):
                permissions = frozenset(
                    str(code).strip()
                    for code in membership.permission_codes
                    if str(code).strip()
                )
                if permissions:
                    scoped_access["project"][membership.project_id] = permissions
            if not scoped_access["project"]:
                scoped_access.pop("project", None)
        project_access = dict(scoped_access.get("project", {}))
        resolved_session_id = (
            str(session_id or "").strip()
            or str(getattr(user, "active_session_id", "") or "").strip()
            or None
        )
        resolved_session = (
            self._auth_session_repo.get(resolved_session_id)
            if self._auth_session_repo is not None and resolved_session_id is not None
            else None
        )
        if resolved_session is not None and resolved_session.revoked_at is not None:
            resolved_session = None
            resolved_session_id = None
        return UserSessionPrincipal(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role_names=frozenset(self.get_user_role_names(user.id)),
            permissions=frozenset(self.get_user_permissions(user.id)),
            scoped_access=scoped_access,
            project_access=project_access,
            session_expires_at=ensure_utc_datetime(
                resolved_session.expires_at if resolved_session is not None else user.session_expires_at
            ),
            must_change_password=bool(user.must_change_password),
            session_revision=int(getattr(user, "session_revision", 1) or 1),
            identity_provider=getattr(user, "identity_provider", None),
            last_login_auth_method=(
                resolved_session.auth_method if resolved_session is not None else getattr(user, "last_login_auth_method", None)
            ),
            session_id=resolved_session_id,
        )

    def _assign_roles_for_user(self, user_id: str, role_names: Iterable[str]) -> None:
        for role_name in role_names:
            role = self._require_role_by_name(role_name)
            if not self._user_role_repo.exists(user_id, role.id):
                self._user_role_repo.add(UserRoleBinding.create(user_id=user_id, role_id=role.id))

    @staticmethod
    def _truthy_env(value: str | None) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}

    def _resolve_bootstrap_admin_password(self) -> str:
        configured = os.getenv("PM_ADMIN_PASSWORD")
        if configured is not None and configured.strip():
            return configured
        if self._truthy_env(os.getenv("PM_ALLOW_DEFAULT_ADMIN_PASSWORD")):
            logger.warning("Bootstrapping admin user with insecure default password because PM_ALLOW_DEFAULT_ADMIN_PASSWORD is enabled.")
            return "ChangeMe123!"
        raise ValidationError(
            "PM_ADMIN_PASSWORD must be set before the first administrator account can be bootstrapped.",
            code="AUTH_BOOTSTRAP_PASSWORD_REQUIRED",
        )

    @staticmethod
    def _normalize_identity_provider(identity_provider: str | None) -> str | None:
        value = str(identity_provider or "").strip().lower()
        return value or None

    @staticmethod
    def _normalize_federated_subject(federated_subject: str | None) -> str | None:
        value = str(federated_subject or "").strip()
        return value or None

    @staticmethod
    def _normalize_device_label(device_label: str | None) -> str | None:
        value = str(device_label or "").strip()
        return value or None

    @staticmethod
    def _validate_federated_identity(
        identity_provider: str | None,
        federated_subject: str | None,
    ) -> None:
        if identity_provider and federated_subject:
            return
        if identity_provider or federated_subject:
            raise ValidationError(
                "Identity provider and federated subject must be set together.",
                code="FEDERATED_IDENTITY_INCOMPLETE",
            )

    @staticmethod
    def _validate_session_timeout_override(value: int | None) -> int | None:
        if value is None:
            return None
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Session timeout override must be an integer number of minutes.",
                code="AUTH_SESSION_TIMEOUT_INVALID",
            ) from exc
        if normalized < 5 or normalized > 1_440:
            raise ValidationError(
                "Session timeout override must be between 5 and 1440 minutes.",
                code="AUTH_SESSION_TIMEOUT_INVALID",
            )
        return normalized

    def _next_session_expiry(self, now: datetime, *, user: UserAccount | None = None) -> datetime:
        timeout_minutes = (
            self._validate_session_timeout_override(getattr(user, "session_timeout_minutes_override", None))
            if user is not None
            else None
        )
        return now + timedelta(minutes=timeout_minutes or session_timeout_minutes())

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

    def _complete_successful_authentication(
        self,
        user: UserAccount,
        *,
        occurred_at: datetime,
        auth_method: str,
        device_label: str | None,
    ) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = occurred_at
        user.last_login_auth_method = auth_method
        user.last_login_device_label = self._normalize_device_label(device_label)
        user.session_expires_at = self._next_session_expiry(occurred_at, user=user)
        user.updated_at = occurred_at
        if self._auth_session_repo is not None:
            auth_session = AuthSession.create(
                user_id=user.id,
                session_revision=int(getattr(user, "session_revision", 1) or 1),
                auth_method=auth_method,
                expires_at=user.session_expires_at,
                device_label=user.last_login_device_label,
            )
            user.active_session_id = auth_session.id
            self._auth_session_repo.add(auth_session)
        else:
            user.active_session_id = None
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        self._record_auth_event(
            action="auth.login.success",
            username=user.username,
            user_id=user.id,
            details={
                "result": "ok",
                "auth_method": auth_method,
                "identity_provider": str(getattr(user, "identity_provider", "") or ""),
                "device_label": str(getattr(user, "last_login_device_label", "") or ""),
                "session_expires_at": user.session_expires_at.isoformat() if user.session_expires_at else "",
            },
        )
        self._refresh_current_session_if_user(user.id)

    def _register_failed_login(
        self,
        user: UserAccount,
        *,
        username: str,
        occurred_at: datetime,
    ) -> None:
        user.failed_login_attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        if user.failed_login_attempts >= login_lockout_threshold():
            user.locked_until = occurred_at + timedelta(minutes=login_lockout_minutes())
        user.updated_at = occurred_at
        self._user_repo.update(user)
        self._session.commit()
        domain_events.auth_changed.emit(user.id)
        if user.locked_until is not None:
            logger.warning(
                "User '%s' locked out until %s after %s failed attempts.",
                username,
                user.locked_until.isoformat(),
                user.failed_login_attempts,
            )

    def _refresh_current_session_if_user(self, user_id: str) -> None:
        if self._user_session is None:
            return
        principal = self._user_session.principal
        if principal is None or principal.user_id != user_id:
            return
        user = self._user_repo.get(user_id)
        if user is None or not user.is_active:
            self._user_session.clear()
            return
        if user.session_expires_at is not None and datetime.now(timezone.utc) >= ensure_utc_datetime(user.session_expires_at):
            self._user_session.clear()
            return
        preferred_session_id = self._resolve_current_principal_session_id(user_id)
        self._user_session.set_principal(self.build_principal(user, session_id=preferred_session_id))

    @staticmethod
    def _rotate_session_revision(user: UserAccount) -> None:
        user.session_revision = max(1, int(getattr(user, "session_revision", 1) or 1)) + 1

    def _enforce_separation_of_duties(self, role_names: Iterable[str]) -> None:
        normalized_role_names = tuple(
            str(role_name or "").strip().lower()
            for role_name in role_names
            if str(role_name or "").strip()
        )
        if "admin" in normalized_role_names:
            return
        permission_codes: set[str] = set()
        for role_name in normalized_role_names:
            role = self._require_role_by_name(role_name)
            permission_codes.update(DEFAULT_ROLE_PERMISSIONS.get(role.name, set()))
        conflicts = self._sod_policy.find_conflicts(permission_codes)
        if conflicts:
            raise ValidationError(
                f"Role assignment violates separation of duties. {conflicts[0]}",
                code="ROLE_CONFLICT",
            )

    def _resolve_current_principal_session_id(self, user_id: str) -> str | None:
        if self._user_session is None:
            return None
        principal = self._user_session.principal
        if principal is None or principal.user_id != user_id:
            return None
        session_id = str(getattr(principal, "session_id", "") or "").strip() or None
        if session_id is None or self._auth_session_repo is None:
            return session_id
        auth_session = self._auth_session_repo.get(session_id)
        if auth_session is None or auth_session.revoked_at is not None:
            return None
        return session_id

    def _revoke_all_persisted_sessions(self, user: UserAccount, *, revoked_at: datetime) -> None:
        if self._auth_session_repo is None:
            return
        for auth_session in self._auth_session_repo.list_by_user(user.id):
            if auth_session.revoked_at is not None:
                continue
            auth_session.revoked_at = revoked_at
            auth_session.updated_at = revoked_at
            self._auth_session_repo.update(auth_session)


__all__ = ["AuthService"]
