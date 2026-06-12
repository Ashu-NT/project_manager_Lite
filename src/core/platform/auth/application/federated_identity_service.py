from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission
from src.core.platform.common.exceptions import ValidationError

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def normalize_identity_provider(identity_provider: str | None) -> str | None:
    value = str(identity_provider or "").strip().lower()
    return value or None


def normalize_federated_subject(federated_subject: str | None) -> str | None:
    value = str(federated_subject or "").strip()
    return value or None


def validate_federated_identity(
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


def link_federated_identity(
    service: AuthService,
    user_id: str,
    *,
    identity_provider: str,
    federated_subject: str,
) -> UserAccount:
    from .session_service import refresh_current_session_if_user

    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="link federated identity",
    )
    user = service._require_user(user_id)
    normalized_provider = normalize_identity_provider(identity_provider)
    normalized_subject = normalize_federated_subject(federated_subject)
    validate_federated_identity(normalized_provider, normalized_subject)
    existing = service._user_repo.get_by_federated_identity(normalized_provider, normalized_subject)
    if existing is not None and existing.id != user.id:
        raise ValidationError(
            "Federated identity is already linked to another user.",
            code="FEDERATED_IDENTITY_EXISTS",
        )
    user.identity_provider = normalized_provider
    user.federated_subject = normalized_subject
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


__all__ = [
    "link_federated_identity",
    "normalize_federated_subject",
    "normalize_identity_provider",
    "validate_federated_identity",
]
