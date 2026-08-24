"""Local Gantt view state updates over the disposable indexed projection."""

from __future__ import annotations

from math import isfinite

from .gantt_selection import set_gantt_selection


def restore_gantt_view_preferences(controller) -> None:
    """Restore validated organization-scoped UI preferences without business work."""
    preferences = controller._app_settings.load_gantt_view_state(
        organization_id=controller._active_organization_id_for_settings(),
    )
    controller._gantt_requested_view_mode = str(preferences["requestedViewMode"])
    controller._gantt_split_ratio = float(preferences["splitRatio"])
    controller._show_dependency_lines = bool(preferences["dependencyLinesEnabled"])
    controller._highlight_critical_tasks = bool(preferences["highlightCriticalTasks"])
    controller._gantt_time_axis.restoreConfiguration(
        str(preferences["timescale"]),
        float(preferences["zoomMultiplier"]),
    )


def persist_gantt_view_preferences(controller) -> None:
    controller._app_settings.save_gantt_view_state(
        {
            "requestedViewMode": controller._gantt_requested_view_mode,
            "splitRatio": controller._gantt_split_ratio,
            "timescale": controller._gantt_time_axis.timescale,
            "zoomMultiplier": controller._gantt_time_axis.zoomMultiplier,
            "dependencyLinesEnabled": controller._show_dependency_lines,
            "highlightCriticalTasks": controller._highlight_critical_tasks,
        },
        organization_id=controller._active_organization_id_for_settings(),
    )


def set_gantt_requested_view_mode(controller, view_mode: str) -> None:
    normalized = str(view_mode or "").strip().lower()
    if normalized not in {"grid", "timeline", "split"}:
        return
    if normalized == controller._gantt_requested_view_mode:
        return
    controller._gantt_requested_view_mode = normalized
    controller.ganttRequestedViewModeChanged.emit()
    persist_gantt_view_preferences(controller)


def set_gantt_split_ratio(controller, ratio: float) -> None:
    try:
        candidate = float(ratio)
    except (TypeError, ValueError):
        return
    if not isfinite(candidate):
        return
    normalized = min(0.62, max(0.44, candidate))
    if abs(normalized - controller._gantt_split_ratio) < 0.000_001:
        return
    controller._gantt_split_ratio = normalized
    controller.ganttSplitRatioChanged.emit()
    persist_gantt_view_preferences(controller)


def set_gantt_timescale(controller, timescale: str) -> bool:
    previous = (
        controller._gantt_time_axis.timescale,
        controller._gantt_time_axis.zoomMultiplier,
    )
    accepted = controller._gantt_time_axis.setTimescale(timescale)
    current = (
        controller._gantt_time_axis.timescale,
        controller._gantt_time_axis.zoomMultiplier,
    )
    if current != previous:
        persist_gantt_view_preferences(controller)
    return accepted


def gantt_zoom_in(controller) -> bool:
    previous = controller._gantt_time_axis.zoomMultiplier
    accepted = controller._gantt_time_axis.zoomIn()
    if controller._gantt_time_axis.zoomMultiplier != previous:
        persist_gantt_view_preferences(controller)
    return accepted


def gantt_zoom_out(controller) -> bool:
    previous = controller._gantt_time_axis.zoomMultiplier
    accepted = controller._gantt_time_axis.zoomOut()
    if controller._gantt_time_axis.zoomMultiplier != previous:
        persist_gantt_view_preferences(controller)
    return accepted


def reset_gantt_zoom(controller) -> bool:
    previous = controller._gantt_time_axis.zoomMultiplier
    accepted = controller._gantt_time_axis.resetZoom()
    if controller._gantt_time_axis.zoomMultiplier != previous:
        persist_gantt_view_preferences(controller)
    return accepted


def refresh_local_gantt_view(controller) -> None:
    """Apply UI-only view state without repository, presenter, or CPM work."""
    model = controller._gantt_model
    model.apply_view(
        search_text=controller._search_text,
        status_filter=controller._selected_status_filter,
        critical_only=controller._show_critical_only,
        delayed_only=controller._show_delayed_only,
        sort_key=controller._activity_sort_key,
        sort_descending=bool(controller._activity_sort_direction),
    )
    if (
        controller._selected_activity_id
        and not model.contains_effective_task(controller._selected_activity_id)
    ):
        set_gantt_selection(controller, "")


def set_gantt_expanded(controller, task_id: str, expanded: bool) -> None:
    """Change hierarchy view state and clear selection if it becomes hidden."""
    controller._gantt_model.set_expanded(task_id, expanded)
    if (
        controller._selected_activity_id
        and not controller._gantt_model.contains_effective_task(
            controller._selected_activity_id
        )
    ):
        set_gantt_selection(controller, "")


__all__ = [
    "gantt_zoom_in",
    "gantt_zoom_out",
    "persist_gantt_view_preferences",
    "refresh_local_gantt_view",
    "reset_gantt_zoom",
    "restore_gantt_view_preferences",
    "set_gantt_expanded",
    "set_gantt_requested_view_mode",
    "set_gantt_split_ratio",
    "set_gantt_timescale",
]
