from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_dispatch_notification(
    owner: object,
    *,
    recipient_user_id: str,
    category: str,
    title: str,
    body: str,
    tenant_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Dispatch a notification without letting delivery failure break the caller.
    """
    notification_service = getattr(owner, "_notification_service", None)
    if notification_service is None:
        return
    normalized_recipient = str(recipient_user_id or "").strip()
    if not normalized_recipient:
        return
    try:
        notification_service.dispatch(
            recipient_user_id=normalized_recipient,
            category=category,
            title=title,
            body=body,
            tenant_id=tenant_id,
            metadata=metadata or {},
            commit=True,
        )
    except Exception:
        logger.exception(
            "Notification dispatch failed category=%s recipient=%s",
            category,
            normalized_recipient,
        )


__all__ = ["safe_dispatch_notification"]
