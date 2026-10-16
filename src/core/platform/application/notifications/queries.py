from __future__ import annotations

from src.core.platform.application.notifications.dto.responses.notification import (
    NotificationDto,
)
from src.core.platform.application.notifications.mappers.notification import (
    map_notification,
)
from src.core.platform.application.notifications.scope import NotificationRecipientScope
from src.core.platform.contract.repositories.notifications.contracts import (
    NotificationRepository,
)


class NotificationQueryHandler:
    """Authenticated personal reads with no delivery or persistence side effects."""

    def __init__(self, *, notification_repo: NotificationRepository, scope: NotificationRecipientScope) -> None:
        self._notification_repo = notification_repo
        self._scope = scope

    def list_my_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationDto]:
        principal = self._scope.require_principal()
        tenant_id, organization_id = self._scope.scope(principal.user_id)
        notifications = self._notification_repo.list_for_user(
            principal.user_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            unread_only=unread_only,
            limit=limit,
        )
        return [map_notification(notification) for notification in notifications]

    def count_my_unread(self) -> int:
        principal = self._scope.require_principal()
        tenant_id, organization_id = self._scope.scope(principal.user_id)
        return self._notification_repo.count_unread_for_user(
            principal.user_id, tenant_id=tenant_id, organization_id=organization_id,
        )

