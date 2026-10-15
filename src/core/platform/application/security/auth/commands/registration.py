from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.auth_validation_policy import (
    AuthValidationPolicy,
)
from src.core.platform.application.security.auth.commands.federated_identity import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from src.core.platform.application.security.auth.dto.commands.users import (
    UserCreateCommand,
)
from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    require_permission,
)
from src.core.platform.application.security.authorization.enforcement.sod_enforcer import (
    SeparationOfDutiesEnforcer,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.application.security.authorization.roles.role_binding_mutation_participant import (
    create_role_binding_using,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.contract.repositories.security.auth import (
    RoleBindingRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    UserTenantMembershipRepository,
)
from src.core.platform.domain.security.auth import UserAccount, normalize_auth_username
from src.core.platform.domain.security.auth.credentials.passwords import hash_password
from src.core.platform.domain.security.auth.events import (
    TenantMembershipProvisioned,
    UserAccountCreated,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBindingPlatformScope,
    RoleBindingTenantScope,
)
from src.core.platform.domain.tenant.tenancy.user_tenant_membership import (
    UserTenantMembership,
)
from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.persistence.unit_of_work import UnitOfWork
from src.core.shared.time.clock import Clock


class UserRegistrationHandler:
    """User registration and tenant onboarding, including initial role bindings,
    separation-of-duties checks and the bootstrap administrator."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        clock: Clock,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        role_binding_repo: RoleBindingRepository | None,
        security_audit_repo: AuditRepository | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        user_tenant_repo: UserTenantMembershipRepository | None,
        validation_policy: AuthValidationPolicy,
        audit: SecurityAuditRecorder,
        sod: SeparationOfDutiesEnforcer,
        target_users: TargetUserAuthorization,
    ) -> None:
        self._tx = tx
        self._clock = clock
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._security_audit_repo = security_audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._user_tenant_repo = user_tenant_repo
        self._validation_policy = validation_policy
        self._audit = audit
        self._sod = sod
        self._target_users = target_users

    def _assign_roles_for_user(
        self,
        user_id: str,
        role_names: Iterable[str],
        *,
        allow_platform_roles: bool,
        tenant_id: str | None,
        record_event: Callable[[DomainEvent], None],
        actor,
    ) -> tuple[str, ...]:
        assigned_role_names: list[str] = []
        for role_name in role_names:
            role = (
                self._role_repo.get_for_tenant_by_name(tenant_id, role_name)
                if tenant_id is not None
                else self._role_repo.get_by_name(role_name)
            )
            if role is None:
                raise ValidationError("Role not found.", code="ROLE_NOT_FOUND")
            if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
                if not allow_platform_roles:
                    authorization_denied(
                        self._user_session,
                        message=(
                            "Platform roles require the dedicated provisioning "
                            "workflow."
                        ),
                        code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                        operation_label="register a platform role holder",
                        target_scope_type="role",
                        target_scope_id=role.id,
                        operation="authorization.platform_role.denied",
                    )
                role_binding_repo = self._role_binding_repo
                if role_binding_repo is None:
                    raise BusinessRuleError(
                        "Canonical role-binding persistence is not configured.",
                        code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                    )
                create_role_binding_using(
                    role_bindings_repo=role_binding_repo,
                    audit_repo=self._security_audit_repo,
                    clock=self._clock,
                    record_event=record_event,
                    principal_id=user_id,
                    role_id=role.id,
                    tenant_id=None,
                    scope_type=ROLE_SCOPE_PLATFORM,
                    scope_id=None,
                    domain_scope=RoleBindingPlatformScope(),
                    actor=actor,
                )
                assigned_role_names.append(role.name)
                continue
            if role.allowed_scope_type == ROLE_SCOPE_TENANT:
                if tenant_id is None:
                    raise BusinessRuleError(
                        "Tenant roles require explicit tenant context.",
                        code="TENANT_CONTEXT_REQUIRED",
                    )
                role_binding_repo = self._role_binding_repo
                if role_binding_repo is None:
                    raise BusinessRuleError(
                        "Canonical role-binding persistence is not configured.",
                        code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                    )
                create_role_binding_using(
                    role_bindings_repo=role_binding_repo,
                    audit_repo=self._security_audit_repo,
                    clock=self._clock,
                    record_event=record_event,
                    principal_id=user_id,
                    role_id=role.id,
                    tenant_id=tenant_id,
                    scope_type=ROLE_SCOPE_TENANT,
                    scope_id=None,
                    domain_scope=RoleBindingTenantScope(tenant_id=tenant_id),
                    actor=actor,
                )
                assigned_role_names.append(role.name)
                continue
            authorization_denied(
                self._user_session,
                message=(
                    f"Role '{role.name}' requires an explicit "
                    f"{role.allowed_scope_type} scope."
                ),
                code="ROLE_SCOPE_REQUIRED",
                operation_label="register a scoped role holder",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.resource_scope.denied",
            )
        return tuple(assigned_role_names)

    def _create_user(
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
        audit_action: str = "user.register",
        system_audit_actor: str | None = None,
        account_type: str = "human",
        uow: UnitOfWork | None = None,
    ) -> UserAccount:
        normalized = normalize_auth_username(username)
        normalized_email = self._validation_policy.normalize_email(email)
        normalized_provider = normalize_identity_provider(identity_provider)
        normalized_subject = normalize_federated_subject(federated_subject)
        self._validation_policy.validate_password(raw_password)
        validate_federated_identity(normalized_provider, normalized_subject)
        if self._user_repo.get_by_username(normalized):
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
        if (
            normalized_provider
            and normalized_subject
            and self._user_repo.get_by_federated_identity(normalized_provider, normalized_subject)
        ):
            raise ValidationError(
                "Federated identity is already linked to another user.",
                code="FEDERATED_IDENTITY_EXISTS",
            )
        resolved_role_names = tuple(
            dict.fromkeys(
                normalized_role_name
                for role_name in (role_names or ())
                if (normalized_role_name := str(role_name or "").strip().lower())
            )
        )
        self._sod.enforce(resolved_role_names)
        if system_audit_actor is None:
            for role_name in resolved_role_names:
                role = self._auth_queries.require_role_by_name(role_name)
                if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
                    authorization_denied(
                        self._user_session,
                        message=(
                            "Platform roles require the dedicated provisioning "
                            "workflow."
                        ),
                        code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                        operation_label="register a platform role holder",
                        target_scope_type="role",
                        target_scope_id=role.id,
                        operation="authorization.platform_role.denied",
                    )
                if role.allowed_scope_type not in {
                    ROLE_SCOPE_PLATFORM,
                    ROLE_SCOPE_TENANT,
                }:
                    authorization_denied(
                        self._user_session,
                        message=(
                            f"Role '{role.name}' requires an explicit "
                            f"{role.allowed_scope_type} scope."
                        ),
                        code="ROLE_SCOPE_REQUIRED",
                        operation_label="register a scoped role holder",
                        target_scope_type="role",
                        target_scope_id=role.id,
                        operation="authorization.resource_scope.denied",
                    )
        user = UserAccount.create(
            username=normalized,
            password_hash=hash_password(raw_password),
            display_name=display_name,
            email=normalized_email,
            is_active=is_active,
            identity_provider=normalized_provider,
            federated_subject=normalized_subject,
            session_timeout_minutes_override=session_timeout_minutes_override,
            must_change_password=must_change_password,
            account_type=account_type,
        )
        normalized_tenant_id = str(tenant_id or "").strip() or None
        if normalized_tenant_id is None:
            requires_tenant = any(
                (
                    candidate_role := self._role_repo.get_by_name(role_name)
                ) is not None
                and candidate_role.allowed_scope_type != ROLE_SCOPE_PLATFORM
                for role_name in resolved_role_names
            )
            if requires_tenant and self._tenant_context_service is not None:
                normalized_tenant_id = (
                    self._tenant_context_service.require_active_tenant_id(
                        operation_label="create a tenant user"
                    )
                )
        if normalized_tenant_id and self._user_tenant_repo is None:
            authorization_denied(
                self._user_session,
                message=(
                    "Tenant membership persistence is required for tenant user "
                    "creation."
                ),
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label="create a tenant user",
                target_scope_type="tenant",
                target_scope_id=normalized_tenant_id,
                operation="authorization.infrastructure.denied",
            )
        owns_uow = uow is None
        active_uow: UnitOfWork = uow if uow is not None else self._tx.uow()
        membership_repo = self._user_tenant_repo
        membership: UserTenantMembership | None = None
        occurred_at = datetime.now(UTC)

        def _run() -> tuple[str, ...]:
            nonlocal membership
            with self._tx.session.begin_nested():
                self._user_repo.add(user)
                self._tx.session.flush()
                if normalized_tenant_id:
                    membership = UserTenantMembership.create(
                        user_id=user.id,
                        tenant_id=normalized_tenant_id,
                    )
                    if membership_repo is None:
                        raise BusinessRuleError(
                            "Tenant membership persistence is required.",
                            code="AUTHORIZATION_CONTEXT_REQUIRED",
                        )
                    membership_repo.add(membership)
                principal = (
                    self._user_session.principal
                    if self._user_session is not None
                    else None
                )
                role_binding_actor = (
                    SimpleNamespace(user_id=None, username=system_audit_actor)
                    if system_audit_actor is not None
                    else principal
                )
                assigned_role_names = self._assign_roles_for_user(
                    user.id,
                    resolved_role_names,
                    allow_platform_roles=system_audit_actor is not None,
                    tenant_id=normalized_tenant_id,
                    record_event=active_uow.record_event,
                    actor=role_binding_actor,
                )
                audit_metadata: dict[str, object] = {
                    "username": user.username,
                    "role_names": list(assigned_role_names),
                    "must_change_password": user.must_change_password,
                }
                if normalized_provider is not None:
                    audit_metadata["identity_provider"] = normalized_provider
                if system_audit_actor is not None:
                    self._audit.add_atomic_system_security_audit(
                        operation="create",
                        entity_type="user",
                        entity_id=user.id,
                        action=audit_action,
                        severity="critical",
                        actor_username=system_audit_actor,
                        metadata=audit_metadata,
                    )
                else:
                    self._audit.add_atomic_security_audit(
                        operation="create",
                        entity_type="user",
                        entity_id=user.id,
                        action=audit_action,
                        severity="high",
                        metadata=audit_metadata,
                        scope_tenant_id=normalized_tenant_id,
                    )
            active_uow.record_event(
                UserAccountCreated(
                    user_id=user.id,
                    tenant_id=normalized_tenant_id,
                    account_type=account_type,
                    occurred_at=occurred_at,
                )
            )
            if membership is not None:
                active_uow.record_event(
                    TenantMembershipProvisioned(
                        membership_id=membership.id,
                        tenant_id=membership.tenant_id,
                        user_id=user.id,
                        occurred_at=occurred_at,
                    )
                )
            return assigned_role_names

        try:
            if owns_uow:
                with active_uow:
                    _run()
                    if commit:
                        active_uow.commit()
            else:
                _run()
        except IntegrityError as exc:
            if "username" in str(exc).lower():
                raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
            raise ValidationError(
                "Failed to create user due to data conflict.",
                code="USER_CREATE_CONFLICT",
            ) from exc
        return user

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
        require_permission(self._user_session, "auth.manage", operation_label="register user")
        return self._create_user(
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

    def onboard_tenant_user(self, command: UserCreateCommand) -> UserAccount:
        username = command.username
        raw_password = command.password
        display_name = command.display_name
        email = command.email
        is_active = command.is_active
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label="onboard tenant user",
        )
        tenant_id = self._target_users.require_actor_active_tenant(
            operation_label="onboard a tenant user",
        )
        return self._create_user(
            username,
            raw_password,
            display_name,
            email,
            is_active,
            ("viewer",),
            True,
            tenant_id=tenant_id,
            audit_action="tenant_user.onboard",
        )

    def register_bootstrap_user(
        self,
        *,
        username: str,
        raw_password: str,
        display_name: str | None = None,
        role_names: Iterable[str] | None = None,
        must_change_password: bool = True,
        commit: bool = False,
        uow: UnitOfWork | None = None,
    ) -> UserAccount:
        return self._create_user(
            username,
            raw_password,
            display_name,
            None,
            True,
            role_names,
            must_change_password,
            commit=commit,
            audit_action="bootstrap.user.register",
            system_audit_actor="local_startup",
            uow=uow,
        )


__all__ = ["UserRegistrationHandler"]
