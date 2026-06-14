from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth_service import AuthService

logger = logging.getLogger(__name__)


def record_auth_event(
    service: AuthService,
    *,
    action: str,
    username: str,
    user_id: str | None,
    details: dict[str, str],
) -> None:
    enterprise_service = getattr(service, "_enterprise_audit_service", None)
    if enterprise_service is not None:
        try:
            enterprise_service.record(
                operation=action,
                entity_type="auth_session",
                entity_id=user_id or username or "unknown",
                module="auth",
                actor_id=user_id,
                actor_username=username or None,
                source="auth",
                severity=_severity_for_action(action),
                compliance_tag="access-control",
                metadata=dict(details),
                commit=True,
            )
            return
        except Exception as exc:
            logger.warning("Failed to write enterprise auth audit event '%s': %s", action, exc)

    legacy_service = getattr(service, "_audit_service", None)
    if legacy_service is None:
        return
    try:
        legacy_service.record(
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


def _severity_for_action(action: str) -> str:
    if "fail" in action or "block" in action or "deny" in action:
        return "high"
    if "logout" in action or "revoke" in action or "expire" in action:
        return "medium"
    return "low"


__all__ = ["record_auth_event"]
