from __future__ import annotations

from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import (
    fmt_utc_datetime,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    serialize_activity_items,
)


def to_activity_feed(feed) -> dict[str, object] | None:
    if feed is None:
        return None
    return {
        "title": feed.title,
        "subtitle": feed.subtitle,
        "emptyState": feed.empty_state,
        "items": serialize_activity_items(_to_activity_item(item) for item in feed.items),
    }


def _to_activity_item(item) -> ActivityItemViewModel:
    is_mention = item.status_label == "Mention"
    return ActivityItemViewModel(
        id=item.id,
        title=item.title,
        actor_display=item.actor_display or "System",
        occurred_at=item.occurred_at,
        occurred_at_label=fmt_utc_datetime(item.occurred_at),
        icon_key="collaboration",
        tone="info" if is_mention else "neutral",
        subject_display=item.subject_display,
        badge_label=item.status_label,
        activation_state={"routeId": item.route_id, **item.state} if item.route_id else None,
    )
