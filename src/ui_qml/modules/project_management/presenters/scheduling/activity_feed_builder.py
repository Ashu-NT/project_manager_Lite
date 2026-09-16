from __future__ import annotations

from typing import Any

from src.ui_qml.shared.models.activity_item import ActivityItemViewModel, serialize_activity_items

from .formatters import format_date, int_label

_TONE_BY_LABEL: dict[str, str] = {
    "Info": "info",
    "Warning": "warning",
    "Danger": "danger",
}


def _item(*, id: str, title: str, status_label: str, subtitle: str, description: str, occurred_at_label: str) -> ActivityItemViewModel:
    return ActivityItemViewModel(
        id=id,
        title=title,
        description=description,
        occurred_at_label=occurred_at_label,
        tone=_TONE_BY_LABEL.get(status_label, "neutral"),
        subject_display=subtitle,
        status_label=status_label,
    )


def build_activity_feed_collection(
    *,
    schedule_items: Any,
    delayed_items: Any,
    resource_load: Any,
    activity_log: tuple[dict[str, str], ...],
) -> dict[str, object]:
    rows: list[ActivityItemViewModel] = [
        _item(
            id=f"log:{index}",
            title=str(entry.get("title", "") or ""),
            status_label=str(entry.get("statusLabel", "") or "Info"),
            subtitle=str(entry.get("subtitle", "") or ""),
            description="",
            occurred_at_label=str(entry.get("metaText", "") or ""),
        )
        for index, entry in enumerate(activity_log, start=1)
        if str(entry.get("title", "") or "").strip()
    ]
    if delayed_items:
        top_delay = delayed_items[0]
        rows.append(
            _item(
                id=f"delay:{top_delay.task_id}",
                title=f"{top_delay.name} is late",
                status_label="Warning",
                subtitle=f"Late by {int_label(top_delay.late_by_days)} day(s)",
                description="Review deadline protection and downstream impact.",
                occurred_at_label=format_date(top_delay.finish_date),
            )
        )
    overloaded = next(
        (item for item in resource_load if float(item.utilization_percent or 0.0) > 100.0),
        None,
    )
    if overloaded is not None:
        rows.append(
            _item(
                id=f"resource:{overloaded.resource_id}",
                title=f"{overloaded.resource_name} exceeds capacity",
                status_label="Danger",
                subtitle=f"Utilization {overloaded.utilization_label}",
                description="Resource leveling or reassignment may be required.",
                occurred_at_label=f"{overloaded.tasks_count} task(s)",
            )
        )
    if not rows and schedule_items:
        rows.append(
            _item(
                id="feed:loaded",
                title="Schedule snapshot loaded",
                status_label="Info",
                subtitle=f"{len(schedule_items)} activities available",
                description="Planner data is ready for review and recalculation.",
                occurred_at_label="Current session",
            )
        )
    return {
        "title": "Planning Activity",
        "subtitle": "Recent planning actions, warnings, and schedule control events.",
        "emptyState": "No planning activity has been recorded in this session.",
        "items": serialize_activity_items(rows[:12]),
    }


__all__ = ["build_activity_feed_collection"]
