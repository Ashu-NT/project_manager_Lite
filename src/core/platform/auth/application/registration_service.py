from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from sqlalchemy.exc import IntegrityError

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import (
    authorization_denied,
    require_permission,
)
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBinding,
    UserAccount,
    normalize_auth_username,
)
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership

if TYPE_CHECKING:
    from .auth_service import AuthService

from .federated_identity_service import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from .security_audit import (
    add_atomic_security_audit,
    add_atomic_system_security_audit,
)
from .sod_enforcer import enforce_separation_of_duties
from .target_user_authorization import require_actor_active_tenant


def _assign_roles_for_user(
    service: AuthService,
    user_id: str,
    role_names: Iterable[str],
    *,
    allow_platform_roles: bool,
    tenant_id: str | None,
    assigned_by: str | None,
) -> tuple[str, ...]:
    assigned_role_names: list[str] = []
    for role_name in role_names:
        role = (
            service._role_repo.get_for_tenant_by_name(tenant_id, role_name)
            if tenant_id is not None
            else service._role_repo.get_by_name(role_name)
        )
        if role is None:
            raise ValidationError("Role not found.", code="ROLE_NOT_FOUND")
        if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
            if not allow_platform_roles:
                authorization_denied(
                    service._user_session,
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
            role_binding_repo = service._role_binding_repo
            if role_binding_repo is None:
                raise BusinessRuleError(
                    "Canonical role-binding persistence is not configured.",
                    code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                )
            if role_binding_repo.get_active_for_assignment(
                principal_id=user_id,
                role_id=role.id,
                tenant_id=None,
                actual_scope_type=ROLE_SCOPE_PLATFORM,
                actual_scope_id=None,
            ) is None:
                role_binding_repo.add(
                    RoleBinding.create(
                        principal_id=user_id,
                        role_id=role.id,
                        actual_scope_type=ROLE_SCOPE_PLATFORM,
                    )
                )
            assigned_role_names.append(role.name)
            continue
        if role.allowed_scope_type == ROLE_SCOPE_TENANT:
            if tenant_id is None:
                raise BusinessRuleError(
                    "Tenant roles require explicit tenant context.",
                    code="TENANT_CONTEXT_REQUIRED",
                )
            role_binding_repo = service._role_binding_repo
            if role_binding_repo is None:
                raise BusinessRuleError(
                    "Canonical role-binding persistence is not configured.",
                    code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                )
            if role_binding_repo.get_active_for_assignment(
                principal_id=user_id,
                role_id=role.id,
                tenant_id=tenant_id,
                actual_scope_type=ROLE_SCOPE_TENANT,
                actual_scope_id=None,
            ) is None:
                role_binding_repo.add(
                    RoleBinding.create(
                        principal_id=user_id,
                        role_id=role.id,
                        tenant_id=tenant_id,
                        actual_scope_type=ROLE_SCOPE_TENANT,
                        assigned_by=assigned_by,
                    )
                )
            assigned_role_names.append(role.name)
            continue
        authorization_denied(
            service._user_session,
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
    service: AuthService,
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
) -> UserAccount:
    normalized = normalize_auth_username(username)
    normalized_email = service._normalize_email(email)
    normalized_provider = normalize_identity_provider(identity_provider)
    normalized_subject = normalize_federated_subject(federated_subject)
    service._validate_password(raw_password)
    validate_federated_identity(normalized_provider, normalized_subject)
    if service._user_repo.get_by_username(normalized):
        raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
    if normalized_provider and normalized_subject:
        if service._user_repo.get_by_federated_identity(normalized_provider, normalized_subject):
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
    enforce_separation_of_duties(service, resolved_role_names)
    if system_audit_actor is None:
        for role_name in resolved_role_names:
            role = service._require_role_by_name(role_name)
            if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
                authorization_denied(
                    service._user_session,
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
                    service._user_session,
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
                role := service._role_repo.get_by_name(role_name)
            ) is not None
            and role.allowed_scope_type != ROLE_SCOPE_PLATFORM
            for role_name in resolved_role_names
        )
        if requires_tenant and service._tenant_context_service is not None:
            normalized_tenant_id = (
                service._tenant_context_service.require_active_tenant_id(
                    operation_label="create a tenant user"
                )
            )
    if normalized_tenant_id and service._user_tenant_repo is None:
        authorization_denied(
            service._user_session,
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
    try:
        with service._session.begin_nested():
            service._user_repo.add(user)
            service._session.flush()
            if normalized_tenant_id:
                membership = UserTenantMembership.create(
                    user_id=user.id,
                    tenant_id=normalized_tenant_id,
                )
                service._user_tenant_repo.add(membership)
            actor = (
                service._user_session.principal
                if service._user_session is not None
                else None
            )
            assigned_role_names = _assign_roles_for_user(
                service,
                user.id,
                resolved_role_names,
                allow_platform_roles=system_audit_actor is not None,
                tenant_id=normalized_tenant_id,
                assigned_by=actor.user_id if actor is not None else None,
            )
            audit_metadata: dict[str, object] = {
                "username": user.username,
                "role_names": list(assigned_role_names),
                "must_change_password": user.must_change_password,
            }
            if normalized_provider is not None:
                audit_metadata["identity_provider"] = normalized_provider
            if system_audit_actor is not None:
                add_atomic_system_security_audit(
                    service,
                    operation="create",
                    entity_type="user",
                    entity_id=user.id,
                    action=audit_action,
                    severity="critical",
                    actor_username=system_audit_actor,
                    metadata=audit_metadata,
                )
            else:
                add_atomic_security_audit(
                    service,
                    operation="create",
                    entity_type="user",
                    entity_id=user.id,
                    action=audit_action,
                    severity="high",
                    metadata=audit_metadata,
                    scope_tenant_id=normalized_tenant_id,
                )
        if commit:
            service._session.commit()
    except IntegrityError as exc:
        service._session.rollback()
        if "username" in str(exc).lower():
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
        raise ValidationError(
            "Failed to create user due to data conflict.",
            code="USER_CREATE_CONFLICT",
        ) from exc
    except Exception:
        service._session.rollback()
        raise
    if commit:
        domain_events.auth_changed.emit(user.id)
    return user


def register_user(
    service: AuthService,
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
    require_permission(service._user_session, "auth.manage", operation_label="register user")
    return _create_user(
        service,
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
    service: AuthService,
    *,
    username: str,
    raw_password: str,
    display_name: str | None = None,
    email: str | None = None,
    is_active: bool = True,
) -> UserAccount:
    require_permission(
        service._user_session,
        "auth.manage",
        operation_label="onboard tenant user",
    )
    tenant_id = require_actor_active_tenant(
        service,
        operation_label="onboard a tenant user",
    )
    return _create_user(
        service,
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


def _register_bootstrap_user(
    service: AuthService,
    *,
    username: str,
    raw_password: str,
    display_name: str | None = None,
    role_names: Iterable[str] | None = None,
    must_change_password: bool = True,
    commit: bool = False,
) -> UserAccount:
    return _create_user(
        service,
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
    )


__all__ = [
    "onboard_tenant_user",
    "register_user",
]
