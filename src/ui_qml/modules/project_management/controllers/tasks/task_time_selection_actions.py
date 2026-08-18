from __future__ import annotations

from .task_lazy_section_loader import load_selected_task_time


def select_assignment(controller, assignment_id: str) -> None:
    """Assignment-section-only selection (docs §44 Time redesign made this
    fully independent of Task Detail -> Time, which no longer has any
    concept of a "selected assignment" -- Log Time picks its own
    assignment locally, and the Overview/Time Entries views are always
    task-scoped across every assignment)."""
    normalized = (assignment_id or "").strip()
    if normalized == controller._selected_assignment_id:
        return
    controller._set_selected_assignment_id(normalized)
    # The previously-selected assignment's capacity preview and project
    # resource usage must never linger against a new (or no) selection --
    # they get refetched by the QML preview-request path right after this,
    # but nothing else clears them on deselect/switch (docs §44 follow-up).
    controller._assignments_ctrl.clearAssignmentPreview()
    controller._assignments_ctrl.clearProjectResourceUsage()


def filter_task_time_entries_by_resource(controller, resource_id: str) -> None:
    normalized = (resource_id or "").strip()
    if normalized == controller._time_resource_filter:
        return
    controller._set_time_resource_filter(normalized)
    controller._set_time_page(1)
    controller._set_selected_time_entry_id("")
    controller._set_time_section_loaded_for_task_id("")
    load_selected_task_time(controller)


def set_task_time_entries_page(controller, page: int) -> None:
    normalized = max(int(page or 1), 1)
    if normalized == controller._time_page:
        return
    controller._set_time_page(normalized)
    controller._set_time_section_loaded_for_task_id("")
    load_selected_task_time(controller)


def select_time_entry(controller, entry_id: str) -> None:
    normalized = (entry_id or "").strip()
    if normalized == controller._selected_time_entry_id:
        return
    controller._set_selected_time_entry_id(normalized)
    controller._set_time_section_loaded_for_task_id("")
    load_selected_task_time(controller)


__all__ = [
    "filter_task_time_entries_by_resource",
    "select_assignment",
    "select_time_entry",
    "set_task_time_entries_page",
]
