from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from sqlalchemy.exc import IntegrityError

from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain import UserAccount, UserRoleBinding, normalize_auth_username
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership

if TYPE_CHECKING:
    from .auth_service import AuthService

from .federated_identity_service import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from .sod_enforcer import enforce_separation_of_duties
from .target_user_authorization import require_actor_active_tenant


def _assign_roles_for_user(service: AuthService, user_id: str, role_names: Iterable[str]) -> None:
    for role_name in role_names:
        role = service._require_role_by_name(role_name)
        if not service._user_role_repo.exists(user_id, role.id):
            service._user_role_repo.add(UserRoleBinding.create(user_id=user_id, role_id=role.id))


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
    resolved_role_names = tuple(role_names or ("viewer",))
    enforce_separation_of_duties(service, resolved_role_names)
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
    )
    normalized_tenant_id = str(tenant_id or "").strip() or None
    try:
        with service._session.begin_nested():
            service._user_repo.add(user)
            _assign_roles_for_user(service, user.id, resolved_role_names)
            if normalized_tenant_id and service._user_tenant_repo is not None:
                membership = UserTenantMembership.create(
                    user_id=user.id,
                    tenant_id=normalized_tenant_id,
                    tenant_role="member",
                )
                service._user_tenant_repo.add(membership)
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
    record_audit_entry(
        service,
        operation="create",
        entity_type="user",
        entity_id=user.id,
        module="platform",
        severity="high",
        compliance_tag="SOC2",
        metadata={
            "action": audit_action,
            "username": user.username,
            "tenant_id": normalized_tenant_id,
        },
    )
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
    )


__all__ = [
    "onboard_tenant_user",
    "register_user",
]
