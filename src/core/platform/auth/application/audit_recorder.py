from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def record_auth_event(
    service,
    *,
    action: str,
    username: str,
    user_id: str | None,
    details: dict[str, str],
) -> None:
    if service._audit_service is None:
        return
    try:
        service._audit_service.record(
            action=action,
            entity_type="auth_session",
            entity_id=user_id or username or "unknown",
            actor_user_id=user_id,
            actor_username=username or None,
            details=details,
            commit=True,
        )
    except Exception as exc:
        logger.warning("Failed to write auth audit event '%s': %s", action, exc)


__all__ = ["record_auth_event"]
