from __future__ import annotations

from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_datetime,
)
from src.ui_qml.shared.models.activity_item import ActivityItemViewModel


def to_recent_action_activity_item(item) -> ActivityItemViewModel:
    return ActivityItemViewModel(
        id=f"{format_datetime(item.occurred_at)}-{item.project_name}-{item.action_label}",
        title=item.action_label,
        description=item.summary,
        actor_display=item.actor_username or "System",
        occurred_at_label=format_datetime(item.occurred_at),
        subject_display=item.project_name,
    )
