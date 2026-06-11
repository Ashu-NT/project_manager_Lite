from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.passwords import hash_password, verify_password
from src.core.platform.common.exceptions import ValidationError

from .session_service import refresh_current_session_if_user, revoke_all_persisted_sessions
from .session_utils import next_session_expiry, rotate_session_revision

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount


def change_password(service, user_id: str, current_password: str, new_password: str) -> None:
    user = service._require_user(user_id)
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")
    service._validate_password(new_password)
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.password_changed_at = user.updated_at
    user.must_change_password = False
    rotate_session_revision(user)
    user.session_expires_at = next_session_expiry(user.updated_at, user=user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


def force_user_password_reset(service, user_id: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="force password reset")
    user = service._require_user(user_id)
    user.must_change_password = True
    user.updated_at = datetime.now(timezone.utc)
    rotate_session_revision(user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)


def reset_user_password(service, user_id: str, new_password: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="reset user password")
    user = service._require_user(user_id)
    service._validate_password(new_password)
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.password_changed_at = user.updated_at
    user.must_change_password = True
    rotate_session_revision(user)
    user.session_expires_at = next_session_expiry(user.updated_at, user=user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


__all__ = ["change_password", "force_user_password_reset", "reset_user_password"]
