"""Local Gantt view state updates over the disposable indexed projection."""

from __future__ import annotations

from .gantt_selection import set_gantt_selection


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


__all__ = ["refresh_local_gantt_view", "set_gantt_expanded"]
