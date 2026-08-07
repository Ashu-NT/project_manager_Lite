from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_any_permission
from src.core.platform.domain.security.auth import (
    normalize_auth_federated_subject,
    normalize_auth_identity_provider,
)
from src.core.platform.common.exceptions import ValidationError

from src.core.platform.application.security.auth.audit.security_audit import add_atomic_security_audit
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import require_target_user_in_active_tenant

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount

    from src.core.platform.application.security.auth.auth_service import AuthService


def normalize_identity_provider(identity_provider: str | None) -> str | None:
    return normalize_auth_identity_provider(identity_provider)


def normalize_federated_subject(federated_subject: str | None) -> str | None:
    return normalize_auth_federated_subject(federated_subject)


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
    from src.core.platform.application.security.auth.session.session_service import refresh_current_session_if_user

    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="link federated identity",
    )
    require_target_user_in_active_tenant(
        service,
        user_id,
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
    updated_user = replace(
        user,
        identity_provider=identity_provider,
        federated_subject=federated_subject,
        updated_at=datetime.now(timezone.utc),
    )
    try:
        service._user_repo.update(updated_user)
        add_atomic_security_audit(
            service,
            operation="update",
            entity_type="user",
            entity_id=updated_user.id,
            action="federated_identity.link",
            severity="high",
            field="identity_provider",
            old_value=user.identity_provider,
            new_value=updated_user.identity_provider,
        )
        service._session.commit()
    except Exception:
        service._session.rollback()
        raise
    domain_events.auth_changed.emit(updated_user.id)
    refresh_current_session_if_user(service, updated_user.id)
    return updated_user


__all__ = [
    "link_federated_identity",
    "normalize_federated_subject",
    "normalize_identity_provider",
    "validate_federated_identity",
]
