from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.core.platform.application.notifications.scope import NotificationRecipientScope
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.notifications.contracts import (
    NotificationRepository,
)
from src.core.platform.domain.notifications import Notification


class NotificationCommandHandler:
    """Owns authenticated, recipient-scoped read-state mutations only."""

    def __init__(self, *, session: Session, notification_repo: NotificationRepository, scope: NotificationRecipientScope) -> None:
        self._session = session
        self._notification_repo = notification_repo
        self._scope = scope

    def mark_read(self, notification_id: str) -> Notification:
        principal = self._scope.require_principal()
        tenant_id, organization_id = self._scope.scope(principal.user_id)
        notification = self._notification_repo.get_for_user(
            str(notification_id or "").strip(), user_id=principal.user_id,
            tenant_id=tenant_id, organization_id=organization_id,
        )
        if notification is None:
            raise NotFoundError(
                "Notification not found.",
                code="NOTIFICATION_NOT_FOUND",
            )
        if notification.read_at is not None:
            return notification
        read_at = datetime.now(UTC)
        self._notification_repo.mark_read(
            notification.id, user_id=principal.user_id,
            tenant_id=tenant_id, organization_id=organization_id, read_at=read_at,
        )
        self._session.commit()
        return replace(notification, read_at=read_at)

    def mark_all_read(self) -> int:
        principal = self._scope.require_principal()
        tenant_id, organization_id = self._scope.scope(principal.user_id)
        read_at = datetime.now(UTC)
        updated = self._notification_repo.mark_all_read_for_user(
            principal.user_id, tenant_id=tenant_id,
            organization_id=organization_id, read_at=read_at,
        )
        self._session.commit()
        return updated
