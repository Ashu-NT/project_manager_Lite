from __future__ import annotations

from .task_lazy_section_loader import load_selected_task_time


def select_assignment(controller, assignment_id: str) -> None:
    normalized = (assignment_id or "").strip()
    if normalized == controller._selected_assignment_id:
        return
    controller._set_selected_assignment_id(normalized)
    controller._set_selected_time_period_start("")
    controller._set_selected_time_entry_id("")
    controller._set_time_section_loaded_for_task_id("")
    # The previously-selected assignment's capacity preview and project
    # resource usage must never linger against a new (or no) selection --
    # they get refetched by the QML preview-request path right after this,
    # but nothing else clears them on deselect/switch (docs §44 follow-up).
    controller._assignments_ctrl.clearAssignmentPreview()
    controller._assignments_ctrl.clearProjectResourceUsage()
    if normalized:
        load_selected_task_time(controller)


def select_time_period(controller, period_start: str) -> None:
    normalized = (period_start or "").strip()
    if normalized == controller._selected_time_period_start:
        return
    controller._set_selected_time_period_start(normalized)
    controller._set_selected_time_entry_id("")
    controller._set_time_section_loaded_for_task_id("")
    load_selected_task_time(controller)


def select_time_entry(controller, entry_id: str) -> None:
    normalized = (entry_id or "").strip()
    if normalized == controller._selected_time_entry_id:
        return
    controller._set_selected_time_entry_id(normalized)
    controller._set_time_section_loaded_for_task_id("")
    load_selected_task_time(controller)


__all__ = ["select_assignment", "select_time_entry", "select_time_period"]
