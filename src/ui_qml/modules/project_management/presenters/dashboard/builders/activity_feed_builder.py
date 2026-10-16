"""Build the bounded collaboration feed directly for QML."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.ui_qml.modules.project_management.presenters.dashboard.activity_feed_mapper import (
    to_activity_item,
)
from src.ui_qml.modules.project_management.presenters.dashboard.formatters.date_formatter import (
    coerce_utc_datetime,
)
from src.ui_qml.modules.project_management.presenters.dashboard.formatters.period_formatter import (
    period_cutoff_datetime,
)
from src.ui_qml.shared.models.activity_item import serialize_activity_items

logger = logging.getLogger(__name__)


def build_preview_activity_feed() -> dict[str, object]:
    return {
        "title": "Recent Activity",
        "subtitle": "Activity stream is not connected for this dashboard preview.",
        "emptyState": "No collaboration activity is available yet.",
        "items": [],
    }


def build_activity_feed(*, project_id: str | None, selected_period_key: str,
                        portfolio_mode: bool, collaboration_inbox_query=None) -> dict[str, object]:
    if collaboration_inbox_query is None:
        return build_preview_activity_feed()
    try:
        recent_activity = collaboration_inbox_query.list_recent_activity(
            project_id=project_id, created_since=period_cutoff_datetime(selected_period_key), limit=120,
        )
    except Exception:
        logger.exception("Failed to load recent activity for project_id=%s, period=%s", project_id, selected_period_key)
        return {**build_preview_activity_feed(), "subtitle": "Activity feed is unavailable for the current session."}
    items = sorted(
        recent_activity,
        key=lambda activity: coerce_utc_datetime(getattr(activity, "created_at", None)) or datetime.now(UTC),
        reverse=True,
    )
    return {
        "title": "Recent Activity",
        "subtitle": (
            "Latest 24 task-collaboration events across the accessible portfolio."
            if portfolio_mode else "Latest 24 task-collaboration events for the selected project."
        ),
        "emptyState": "No recent dashboard activity is available in the selected period.",
        "items": serialize_activity_items(to_activity_item(item) for item in items[:24]),
    }
