from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from sqlalchemy.orm import Session

from src.core.platform.access.contracts import (
    ProjectMembershipRepository,
    ScopedAccessGrantRepository,
)
from src.core.platform.auth.application.auth_query import AuthQueryMixin
from src.core.platform.auth.application.auth_validation import AuthValidationMixin
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.domain import AuthSession, Role, UserAccount
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.auth.sod import SeparationOfDutiesPolicy

from . import authentication_service as _auth
from . import bootstrap_service as _bootstrap
from . import federated_identity_service as _fed
from . import mfa_service as _mfa
from . import password_service as _pw
from . import principal_builder as _principal
from . import registration_service as _reg
from . import role_assignment_service as _roles
from . import session_service as _sessions
from . import user_admin_service as _users

if TYPE_CHECKING:
    from src.core.platform.audit.application.audit_service import AuditService


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
        return _bootstrap.bootstrap_defaults(self)

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
        return _reg.register_user(
            self,
            username,
            raw_password,
            display_name,
            email,
            is_active,
            role_names,
            must_change_password,
            identity_provider=identity_provider,
            federated_subject=federated_subject,
            session_timeout_minutes_override=session_timeout_minutes_override,
            commit=commit,
            bypass_permission=bypass_permission,
        )

    def authenticate(
        self,
        username: str,
        raw_password: str,
        *,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        return _auth.authenticate(self, username, raw_password, mfa_code=mfa_code, device_label=device_label)

    def authenticate_federated(
        self,
        *,
        identity_provider: str,
        federated_subject: str,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        return _auth.authenticate_federated(
            self,
            identity_provider=identity_provider,
            federated_subject=federated_subject,
            mfa_code=mfa_code,
            device_label=device_label,
        )

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        _pw.change_password(self, user_id, current_password, new_password)

    def force_user_password_reset(self, user_id: str) -> None:
        _pw.force_user_password_reset(self, user_id)

    def reset_user_password(self, user_id: str, new_password: str) -> None:
        _pw.reset_user_password(self, user_id, new_password)

    def assign_role(self, user_id: str, role_name: str) -> None:
        _roles.assign_role(self, user_id, role_name)

    def revoke_role(self, user_id: str, role_name: str) -> None:
        _roles.revoke_role(self, user_id, role_name)

    def list_users(self) -> list[UserAccount]:
        return _users.list_users(self)

    def list_roles(self) -> list[Role]:
        return _users.list_roles(self)

    def set_user_active(self, user_id: str, is_active: bool) -> UserAccount:
        return _users.set_user_active(self, user_id, is_active)

    def update_user_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> UserAccount:
        return _users.update_user_profile(self, user_id, username=username, display_name=display_name, email=email)

    def unlock_user_account(self, user_id: str) -> UserAccount:
        return _users.unlock_user_account(self, user_id)

    def link_federated_identity(
        self,
        user_id: str,
        *,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount:
        return _fed.link_federated_identity(
            self, user_id, identity_provider=identity_provider, federated_subject=federated_subject
        )

    def provision_mfa_secret(self, user_id: str) -> str:
        return _mfa.provision_mfa_secret(self, user_id)

    def enable_user_mfa(self, user_id: str, verification_code: str) -> UserAccount:
        return _mfa.enable_user_mfa(self, user_id, verification_code)

    def disable_user_mfa(self, user_id: str) -> UserAccount:
        return _mfa.disable_user_mfa(self, user_id)

    def set_user_session_policy(
        self,
        user_id: str,
        *,
        session_timeout_minutes_override: int | None,
    ) -> UserAccount:
        return _sessions.set_user_session_policy(
            self, user_id, session_timeout_minutes_override=session_timeout_minutes_override
        )

    def revoke_user_sessions(self, user_id: str, *, note: str = "") -> UserAccount:
        return _sessions.revoke_user_sessions(self, user_id, note=note)

    def list_user_sessions(self, user_id: str) -> list[AuthSession]:
        return _sessions.list_user_sessions(self, user_id)

    def revoke_session(self, session_id: str, *, note: str = "") -> AuthSession:
        return _sessions.revoke_session(self, session_id, note=note)

    def validate_session_principal(self, principal: UserSessionPrincipal) -> UserSessionPrincipal | None:
        return _sessions.validate_session_principal(self, principal)

    def persist_session_context(self, session_context: UserSessionContext) -> None:
        _sessions.persist_session_context(self, session_context)

    def build_principal(self, user: UserAccount, *, session_id: str | None = None) -> UserSessionPrincipal:
        return _principal.build_principal(self, user, session_id=session_id)


__all__ = ["AuthService"]
