from __future__ import annotations

from .gantt_selection import set_gantt_selection
from .gantt_baseline_actions import clear_gantt_baseline
from .gantt_view_state import refresh_local_gantt_view, set_gantt_expanded
from .scheduling_property_updates import (
    set_activity_sort_direction,
    set_activity_sort_key,
    set_baseline_variance_rows,
    set_baselines,
    set_search_text,
    set_selected_baseline_id,
    set_selected_calendar_id,
    set_selected_project_id,
    set_selected_status_filter,
    set_show_critical_only,
    set_show_delayed_only,
)


def set_active_panel(controller, panel_id: str) -> None:
    normalized = (panel_id or "").strip() or "overview"
    if normalized == controller._active_panel_id:
        return
    controller._active_panel_id = normalized
    controller.refresh()


def select_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip()
    if normalized == controller._selected_project_id:
        return
    clear_gantt_baseline(controller, clear_selection=True)
    set_selected_project_id(controller, normalized)
    set_selected_baseline_id(controller, "")
    set_gantt_selection(controller, "")
    set_baselines(controller, {
        **controller._baselines,
        "selectedBaselineAId": "",
        "selectedBaselineBId": "",
        "includeUnchanged": False,
    })
    controller._activity_log_svc.reset()
    set_baseline_variance_rows(controller, [])
    controller.refresh()


def select_calendar(controller, calendar_id: str) -> None:
    normalized = (calendar_id or "").strip() or "default"
    if normalized == controller._selected_calendar_id:
        return
    set_selected_calendar_id(controller, normalized)
    controller.refresh()


def select_baseline(controller, baseline_id: str) -> None:
    normalized = (baseline_id or "").strip()
    if normalized == controller._selected_baseline_id:
        return
    set_selected_baseline_id(controller, normalized)
    set_baselines(controller, {**controller._baselines, "selectedBaselineAId": normalized})
    controller.refresh()


def select_baseline_a(controller, baseline_id: str) -> None:
    normalized = (baseline_id or "").strip()
    if normalized == str(controller._baselines.get("selectedBaselineAId") or ""):
        return
    set_baselines(controller, {**controller._baselines, "selectedBaselineAId": normalized})
    controller.refresh()


def select_baseline_b(controller, baseline_id: str) -> None:
    normalized = (baseline_id or "").strip()
    if normalized == str(controller._baselines.get("selectedBaselineBId") or ""):
        return
    set_baselines(controller, {**controller._baselines, "selectedBaselineBId": normalized})
    controller.refresh()


def set_include_unchanged(controller, include_unchanged: bool) -> None:
    if bool(controller._baselines.get("includeUnchanged", False)) == include_unchanged:
        return
    set_baselines(controller, {**controller._baselines, "includeUnchanged": include_unchanged})
    controller.refresh()


def apply_search_text(controller, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == controller._search_text:
        return
    set_search_text(controller, normalized)
    refresh_local_gantt_view(controller)


def apply_status_filter(controller, status_filter: str) -> None:
    normalized = (status_filter or "").strip() or "all"
    if normalized == controller._selected_status_filter:
        return
    set_selected_status_filter(controller, normalized)
    refresh_local_gantt_view(controller)


def apply_show_critical_only(controller, enabled: bool) -> None:
    if enabled == controller._show_critical_only:
        return
    set_show_critical_only(controller, enabled)
    refresh_local_gantt_view(controller)


def apply_show_delayed_only(controller, enabled: bool) -> None:
    if enabled == controller._show_delayed_only:
        return
    set_show_delayed_only(controller, enabled)
    refresh_local_gantt_view(controller)


def clear_filters(controller) -> None:
    if (
        not controller._search_text
        and controller._selected_status_filter == "all"
        and not controller._show_critical_only
        and not controller._show_delayed_only
    ):
        return
    set_search_text(controller, "")
    set_selected_status_filter(controller, "all")
    set_show_critical_only(controller, False)
    set_show_delayed_only(controller, False)
    refresh_local_gantt_view(controller)


def select_activity(controller, activity_id: str) -> None:
    set_gantt_selection(controller, activity_id)


def activate_activity(controller, activity_id: str) -> None:
    select_activity(controller, activity_id)


def set_hierarchy_expanded(controller, task_id: str, expanded: bool) -> None:
    set_gantt_expanded(controller, task_id, expanded)


def set_activity_sort(controller, sort_key: str, sort_direction: int) -> None:
    normalized_key = (sort_key or "").strip()
    normalized_direction = 1 if sort_direction == 1 else 0
    if not normalized_key:
        return
    if (
        normalized_key == controller._activity_sort_key
        and normalized_direction == controller._activity_sort_direction
    ):
        return
    set_activity_sort_key(controller, normalized_key)
    set_activity_sort_direction(controller, normalized_direction)
    refresh_local_gantt_view(controller)


__all__ = [
    "activate_activity",
    "apply_search_text",
    "apply_show_critical_only",
    "apply_show_delayed_only",
    "apply_status_filter",
    "clear_filters",
    "select_activity",
    "select_baseline",
    "select_baseline_a",
    "select_baseline_b",
    "select_calendar",
    "select_project",
    "set_active_panel",
    "set_activity_sort",
    "set_hierarchy_expanded",
    "set_include_unchanged",
]
