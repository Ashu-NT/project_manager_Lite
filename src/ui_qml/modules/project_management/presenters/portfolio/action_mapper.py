from __future__ import annotations

from src.ui_qml.shared.models.activity_item import ActivityItemViewModel


def to_recent_action_activity_item(item) -> ActivityItemViewModel:
    return ActivityItemViewModel(
        id=f"{item.occurred_at_label}-{item.project_name}-{item.action_label}",
        title=item.action_label,
        description=item.summary,
        actor_display=item.actor_username or "System",
        occurred_at_label=item.occurred_at_label,
        subject_display=item.project_name,
    )
