from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
    SchedulingRecordViewModel,
)

from .formatters import format_date, int_label


def build_activity_feed_collection(
    *,
    schedule_items,
    delayed_items,
    resource_load,
    activity_log: tuple[dict[str, str], ...],
) -> SchedulingCollectionViewModel:
    rows: list[SchedulingRecordViewModel] = [
        SchedulingRecordViewModel(
            id=f"log:{index}",
            title=str(item.get("title", "") or ""),
            status_label=str(item.get("statusLabel", "") or "Info"),
            subtitle=str(item.get("subtitle", "") or ""),
            supporting_text="",
            meta_text=str(item.get("metaText", "") or ""),
        )
        for index, item in enumerate(activity_log, start=1)
        if str(item.get("title", "") or "").strip()
    ]
    if delayed_items:
        top_delay = delayed_items[0]
        rows.append(
            SchedulingRecordViewModel(
                id=f"delay:{top_delay.id}",
                title=f"{top_delay.name} is late",
                status_label="Warning",
                subtitle=f"Late by {int_label(top_delay.late_by_days)} day(s)",
                supporting_text="Review deadline protection and downstream impact.",
                meta_text=format_date(top_delay.finish_date),
            )
        )
    overloaded = next(
        (item for item in resource_load if float(item.utilization_percent or 0.0) > 100.0),
        None,
    )
    if overloaded is not None:
        rows.append(
            SchedulingRecordViewModel(
                id=f"resource:{overloaded.resource_id}",
                title=f"{overloaded.resource_name} exceeds capacity",
                status_label="Danger",
                subtitle=f"Utilization {overloaded.utilization_label}",
                supporting_text="Resource leveling or reassignment may be required.",
                meta_text=f"{overloaded.tasks_count} task(s)",
            )
        )
    if not rows and schedule_items:
        rows.append(
            SchedulingRecordViewModel(
                id="feed:loaded",
                title="Schedule snapshot loaded",
                status_label="Info",
                subtitle=f"{len(schedule_items)} activities available",
                supporting_text="Planner data is ready for review and recalculation.",
                meta_text="Current session",
            )
        )
    return SchedulingCollectionViewModel(
        title="Planning Activity",
        subtitle="Recent planning actions, warnings, and schedule control events.",
        items=tuple(rows[:12]),
        empty_state="No planning activity has been recorded in this session.",
    )


__all__ = ["build_activity_feed_collection"]
