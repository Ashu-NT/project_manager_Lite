from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.core.platform.auth.application.auth_query import AuthQueryMixin
from src.core.platform.auth.application.auth_validation import AuthValidationMixin
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.auth.domain import AuthSession, Role, UserAccount
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.auth.sod import SeparationOfDutiesPolicy
from src.core.platform.common.exceptions import BusinessRuleError

from . import authentication_service as _auth
from . import bootstrap_service as _bootstrap
from . import context_switch_service as _context_switch
from . import federated_identity_service as _fed
from . import mfa_service as _mfa
from . import password_service as _pw
from . import platform_owner_provisioning_service as _platform_owner
from . import principal_builder as _principal
from . import registration_service as _reg
from . import role_assignment_service as _roles
from . import session_service as _sessions
from . import user_admin_service as _users
from .canonical_role_resolver import CanonicalRoleResolver, ScopeTenantResolver

if TYPE_CHECKING:
    from src.core.platform.audit.application.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.audit.contracts import AuditRepository
    from src.core.platform.tenancy.contracts import UserTenantMembershipRepository
    from src.core.platform.tenancy.tenant_context import TenantContextService

    from .role_governance_service import RoleGovernanceService


class AuthService(AuthQueryMixin, AuthValidationMixin):
    def __init__(
        self,
        session: Session,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        auth_session_repo: AuthSessionRepository | None = None,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: "EnterpriseAuditService | None" = None,
        security_audit_repo: "AuditRepository | None" = None,
        sod_policy: SeparationOfDutiesPolicy | None = None,
        user_tenant_repo: "UserTenantMembershipRepository | None" = None,
        tenant_context_service: "TenantContextService | None" = None,
        request_id_provider: Callable[[], str | None] | None = None,
        role_binding_repo: RoleBindingRepository | None = None,
        canonical_scope_tenant_resolvers: Mapping[
            str,
            ScopeTenantResolver,
        ] | None = None,
        allow_platform_customer_context: bool = False,
    ):
        self._session: Session = session
        self._user_repo: UserRepository = user_repo
        self._role_repo: RoleRepository = role_repo
        self._permission_repo: PermissionRepository = permission_repo
        self._role_permission_repo: RolePermissionRepository = role_permission_repo
        self._auth_session_repo: AuthSessionRepository | None = auth_session_repo
        self._user_session: UserSessionContext | None = user_session
        self._enterprise_audit_service: EnterpriseAuditService | None = enterprise_audit_service
        self._security_audit_repo: AuditRepository | None = security_audit_repo
        self._sod_policy = sod_policy or SeparationOfDutiesPolicy()
        self._user_tenant_repo: "UserTenantMembershipRepository | None" = user_tenant_repo
        self._tenant_context_service: "TenantContextService | None" = (
            tenant_context_service
        )
        self._request_id_provider = request_id_provider
        self._role_binding_repo = role_binding_repo
        self._allow_platform_customer_context = bool(
            allow_platform_customer_context
        )
        self._canonical_role_resolver = (
            CanonicalRoleResolver(
                role_binding_repo=role_binding_repo,
                role_repo=role_repo,
                role_permission_repo=role_permission_repo,
                permission_repo=permission_repo,
                scope_tenant_resolvers=(canonical_scope_tenant_resolvers or {}),
                allow_platform_customer_context=(
                    self._allow_platform_customer_context
                ),
            )
            if role_binding_repo is not None
            else None
        )
        self._role_governance_service: RoleGovernanceService | None = None

    def register_canonical_scope_tenant_resolver(
        self,
        scope_type: str,
        resolver: ScopeTenantResolver,
    ) -> None:
        self._require_canonical_role_resolver().register_scope_tenant_resolver(
            scope_type, resolver
        )

    def _require_canonical_role_resolver(self) -> CanonicalRoleResolver:
        if self._canonical_role_resolver is None:
            raise BusinessRuleError(
                "Canonical role-binding persistence is not configured.",
                code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
            )
        return self._canonical_role_resolver

    def set_role_governance_service(
        self,
        role_governance_service: RoleGovernanceService,
    ) -> None:
        self._role_governance_service = role_governance_service

    def _require_role_governance_service(self) -> RoleGovernanceService:
        if self._role_governance_service is None:
            raise BusinessRuleError(
                "Canonical role governance is not configured.",
                code="AUTHORIZATION_GOVERNANCE_REQUIRED",
            )
        return self._role_governance_service

    def bootstrap_defaults(self) -> UserAccount:
        return _bootstrap.bootstrap_defaults(self)

    def bootstrap_policy_catalog(self) -> None:
        _bootstrap.bootstrap_policy_catalog(self)

    def provision_platform_owner(
        self,
        *,
        username: str,
        raw_password: str,
        audit_writer: _platform_owner.PlatformAuditWriter,
        display_name: str = "Platform Owner",
        email: str | None = None,
        provisioning_actor: str = "deployment",
    ) -> _platform_owner.PlatformOwnerProvisioningResult:
        return _platform_owner.provision_platform_owner(
            self,
            username=username,
            raw_password=raw_password,
            audit_writer=audit_writer,
            display_name=display_name,
            email=email,
            provisioning_actor=provisioning_actor,
        )

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
        tenant_id: str | None = None,
        commit: bool = True,
        account_type: str = "human",
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
            tenant_id=tenant_id,
            commit=commit,
            account_type=account_type,
        )

    def onboard_tenant_user(
        self,
        *,
        username: str,
        raw_password: str,
        display_name: str | None = None,
        email: str | None = None,
        is_active: bool = True,
    ) -> UserAccount:
        return _reg.onboard_tenant_user(
            self,
            username=username,
            raw_password=raw_password,
            display_name=display_name,
            email=email,
            is_active=is_active,
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

    def assign_customer_role(self, user_id: str, role_name: str) -> None:
        _roles.assign_customer_role(self, user_id, role_name)

    def revoke_customer_role(self, user_id: str, role_name: str) -> None:
        _roles.revoke_customer_role(self, user_id, role_name)

    def list_users(self) -> list[UserAccount]:
        return _users.list_users(self)

    def list_roles(self) -> list[Role]:
        return _users.list_roles(self)

    def list_customer_assignable_roles(self) -> list[Role]:
        return _users.list_customer_assignable_roles(self)

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

    def commit_context_switch(
        self,
        target_principal: UserSessionPrincipal,
        switch_type: str,
    ) -> None:
        _context_switch.commit_context_switch(
            self,
            target_principal,
            switch_type=switch_type,
        )

    def build_principal(self, user: UserAccount, *, session_id: str | None = None) -> UserSessionPrincipal:
        return _principal.build_principal(self, user, session_id=session_id)

    def build_principal_for_context(
        self,
        user: UserAccount,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        session_id: str | None = None,
    ) -> UserSessionPrincipal:
        return _principal.build_principal(
            self,
            user,
            session_id=session_id,
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )

    def rebuild_current_principal_for_context(
        self,
        tenant_id: str,
        organization_id: str | None,
    ) -> UserSessionPrincipal:
        if self._user_session is None or self._user_session.principal is None:
            raise BusinessRuleError(
                "Authentication is required to rebuild tenant authority.",
                code="AUTHENTICATION_REQUIRED",
            )
        current = self._user_session.principal
        user = self._require_user(current.user_id)
        return self.build_principal_for_context(
            user,
            tenant_id=tenant_id,
            organization_id=organization_id,
            session_id=current.session_id,
        )


__all__ = ["AuthService"]
