from __future__ import annotations

from copy import deepcopy

from src.core.platform.application.notifications.dto.responses.notification import (
    NotificationDto,
)
from src.core.platform.domain.notifications import Notification


def map_notification(notification: Notification) -> NotificationDto:
    return NotificationDto(
        id=notification.id,
        category=notification.category,
        title=notification.title,
        body=notification.body,
        created_at=notification.created_at,
        read_at=notification.read_at,
        is_read=notification.is_read,
        metadata=deepcopy(notification.metadata),
    )
