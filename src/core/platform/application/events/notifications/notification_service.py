from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.events.notifications.contracts import NotificationChannel, NotificationRepository
from src.core.platform.domain.events.notifications import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """In-app notification dispatch, with a zero-or-more external-channel fan-out."""

    def __init__(
        self,
        *,
        session: Session,
        notification_repo: NotificationRepository,
        user_session: UserSessionContext | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> None:
        self._session = session
        self._notification_repo = notification_repo
        self._user_session = user_session
        self._channels = list(channels or [])

    def dispatch(
        self,
        *,
        recipient_user_id: str,
        category: str,
        title: str,
        body: str,
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> Notification:
        normalized_recipient_id = str(recipient_user_id or "").strip()
        if not normalized_recipient_id:
            raise BusinessRuleError(
                "A notification requires a recipient.",
                code="NOTIFICATION_RECIPIENT_REQUIRED",
            )
        notification = Notification.create(
            recipient_user_id=normalized_recipient_id,
            category=category,
            title=title,
            body=body,
            tenant_id=tenant_id,
            metadata=metadata,
        )
        self._notification_repo.add(notification)
        if commit:
            self._session.commit()
        for channel in self._channels:
            try:
                channel.send(notification)
            except Exception:
                logger.exception(
                    "Notification channel delivery failed category=%s channel=%s",
                    category,
                    type(channel).__name__,
                )
        return notification

    def list_my_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        principal = self._require_principal()
        return self._notification_repo.list_for_user(
            principal.user_id,
            unread_only=unread_only,
            limit=limit,
        )

    def mark_read(self, notification_id: str) -> Notification:
        principal = self._require_principal()
        notification = self._notification_repo.get(str(notification_id or "").strip())
        if notification is None or notification.recipient_user_id != principal.user_id:
            raise NotFoundError(
                "Notification not found.",
                code="NOTIFICATION_NOT_FOUND",
            )
        if notification.read_at is not None:
            return notification
        read_at = datetime.now(timezone.utc)
        self._notification_repo.mark_read(notification.id, read_at=read_at)
        self._session.commit()
        return replace(notification, read_at=read_at)

    def _require_principal(self):
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required to view notifications.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal


__all__ = ["NotificationService"]
