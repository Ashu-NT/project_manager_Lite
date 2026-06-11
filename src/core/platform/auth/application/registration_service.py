from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from sqlalchemy.exc import IntegrityError

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain import UserAccount, UserRoleBinding
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import ValidationError

from .federated_identity_service import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from .session_utils import validate_session_timeout_override
from .sod_enforcer import enforce_separation_of_duties


def assign_roles_for_user(service, user_id: str, role_names: Iterable[str]) -> None:
    for role_name in role_names:
        role = service._require_role_by_name(role_name)
        if not service._user_role_repo.exists(user_id, role.id):
            service._user_role_repo.add(UserRoleBinding.create(user_id=user_id, role_id=role.id))


def register_user(
    service,
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
        require_permission(service._user_session, "auth.manage", operation_label="register user")
    normalized = (username or "").strip().lower()
    normalized_email = service._normalize_email(email)
    normalized_provider = normalize_identity_provider(identity_provider)
    normalized_subject = normalize_federated_subject(federated_subject)
    if not normalized:
        raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
    service._validate_email(normalized_email)
    service._validate_password(raw_password)
    validate_federated_identity(normalized_provider, normalized_subject)
    resolved_session_timeout = validate_session_timeout_override(session_timeout_minutes_override)
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
        display_name=(display_name or "").strip() or None,
        email=normalized_email,
        is_active=is_active,
    )
    user.must_change_password = bool(must_change_password)
    user.identity_provider = normalized_provider
    user.federated_subject = normalized_subject
    user.session_timeout_minutes_override = resolved_session_timeout
    try:
        with service._session.begin_nested():
            service._user_repo.add(user)
            assign_roles_for_user(service, user.id, resolved_role_names)
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
    domain_events.auth_changed.emit(user.id)
    return user


__all__ = ["assign_roles_for_user", "register_user"]
