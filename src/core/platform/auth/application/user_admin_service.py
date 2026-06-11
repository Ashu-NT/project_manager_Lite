from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.auth.domain import Role, UserAccount
from src.core.platform.common.exceptions import ValidationError

from .session_service import refresh_current_session_if_user


def list_users(service) -> list[UserAccount]:
    require_any_permission(
        service._user_session,
        ("auth.manage", "auth.read", "access.manage", "security.manage"),
        operation_label="list users",
    )
    return service._user_repo.list_all()


def list_roles(service) -> list[Role]:
    require_any_permission(
        service._user_session,
        ("auth.manage", "auth.read"),
        operation_label="list roles",
    )
    return service._role_repo.list_all()


def set_user_active(service, user_id: str, is_active: bool) -> UserAccount:
    require_permission(service._user_session, "auth.manage", operation_label="set user active")
    user = service._require_user(user_id)
    user.is_active = bool(is_active)
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def update_user_profile(
    service,
    user_id: str,
    *,
    username: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
) -> UserAccount:
    require_permission(service._user_session, "auth.manage", operation_label="update user profile")
    user = service._require_user(user_id)
    if username is not None:
        normalized = (username or "").strip().lower()
        if not normalized:
            raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
        existing = service._user_repo.get_by_username(normalized)
        if existing and existing.id != user.id:
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
        user.username = normalized
    if display_name is not None:
        user.display_name = (display_name or "").strip() or None
    if email is not None:
        normalized_email = service._normalize_email(email)
        service._validate_email(normalized_email)
        user.email = normalized_email
    user.updated_at = datetime.now(timezone.utc)
    try:
        service._user_repo.update(user)
        service._session.commit()
    except IntegrityError as exc:
        service._session.rollback()
        if "username" in str(exc).lower():
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
        raise ValidationError(
            "Failed to update user due to data conflict.",
            code="USER_UPDATE_CONFLICT",
        ) from exc
    except Exception:
        service._session.rollback()
        raise
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def unlock_user_account(service, user_id: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="unlock user account",
    )
    user = service._require_user(user_id)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


__all__ = [
    "list_roles",
    "list_users",
    "set_user_active",
    "unlock_user_account",
    "update_user_profile",
]
