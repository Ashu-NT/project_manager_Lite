"""Notification results never expose a mutable domain notification."""

from dataclasses import replace
from datetime import UTC, datetime

from src.core.platform.application.notifications.mappers.notification import (
    map_notification,
)
from src.core.platform.domain.notifications import Notification


def test_mapping_detaches_nested_metadata_and_preserves_zero_values():
    notification = Notification(
        id="notice", recipient_user_id="recipient", tenant_id="tenant",
        category="notice", title="Notice", body="Body",
        created_at=datetime(2026, 10, 16, tzinfo=UTC),
        metadata={"count": 0, "context": {"ids": ["original"]}},
    )
    response = map_notification(notification)
    assert response.metadata["count"] == 0
    response.metadata["context"]["ids"].append("response-only")
    assert notification.metadata["context"]["ids"] == ["original"]
    assert map_notification(replace(notification, read_at=notification.created_at)).is_read
