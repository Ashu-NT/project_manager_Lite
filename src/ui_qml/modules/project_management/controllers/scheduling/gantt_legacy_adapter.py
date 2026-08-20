"""TEMPORARY R4.5B adapter feeding the pre-R4.5C visual Gantt surface.

Removal owner: R4.5C. Delete this file and its imports when the specialized
Gantt viewport consumes ``GanttListModel`` directly. It must not survive the
retirement of the paginated DataTable + SchedulingTimelinePanel pair.
"""

from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_scheduling_collection_view_model,
)
from src.ui_qml.modules.project_management.presenters.scheduling.record_mappers import (
    to_schedule_record,
    to_timeline_record,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
)

from .gantt_selection import set_gantt_selection
from .row_builders import build_schedule_rows
from .scheduling_property_updates import (
    set_activity_page,
    set_activity_total_count,
    set_schedule,
    set_schedule_rows,
    set_timeline,
)


def refresh_local_gantt_view(controller) -> None:
    """Apply view-only operations without rebuilding the authoritative projection."""
    model = controller._gantt_model
    model.apply_view(
        search_text=controller._search_text,
        status_filter=controller._selected_status_filter,
        critical_only=controller._show_critical_only,
        delayed_only=controller._show_delayed_only,
        sort_key=controller._activity_sort_key,
        sort_descending=bool(controller._activity_sort_direction),
    )
    rows = model.filtered_leaf_rows()
    total_count = len(rows)
    page_size = max(10, int(controller._activity_page_size or 25))
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    page = min(max(1, int(controller._activity_page or 1)), total_pages)
    page_start = (page - 1) * page_size
    visible_rows = rows[page_start : page_start + page_size]
    all_project_leaves = tuple(row for row in model.all_rows if not row.is_summary)
    calendar_label = str(controller._calendar.get("calendarName", "") or "Default Calendar")
    if not model.projectId:
        empty_state = "Select a project to review the schedule."
    elif not all_project_leaves:
        empty_state = "No scheduled activities are available for the selected project."
    else:
        empty_state = "No activities match the current planning filters."
    schedule = SchedulingCollectionViewModel(
        title="Activities",
        subtitle="Current planning window with CPM, float, constraint, and progress context.",
        items=tuple(
            to_schedule_record(
                row,
                row_index=page_start + index,
                calendar_label=calendar_label,
            )
            for index, row in enumerate(visible_rows, start=1)
        ),
        empty_state=empty_state,
    )
    timeline = SchedulingCollectionViewModel(
        title="Timeline",
        subtitle="Current schedule bars and explicit milestone markers.",
        items=tuple(
            to_timeline_record(row, timeline_items=all_project_leaves)
            for row in visible_rows
        ),
        empty_state=empty_state,
    )
    serialized_schedule = serialize_scheduling_collection_view_model(schedule)
    set_activity_page(controller, page)
    set_activity_total_count(controller, total_count)
    set_schedule(controller, serialized_schedule)
    set_timeline(controller, serialize_scheduling_collection_view_model(timeline))
    set_schedule_rows(controller, build_schedule_rows(serialized_schedule))
    if (
        controller._selected_activity_id
        and not model.contains_filtered_task(controller._selected_activity_id)
    ):
        set_gantt_selection(controller, "")


__all__ = ["refresh_local_gantt_view"]
