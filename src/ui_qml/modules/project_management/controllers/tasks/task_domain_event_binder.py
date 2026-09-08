from __future__ import annotations

from .task_lazy_section_loader import (
    load_selected_task_assignments,
    load_selected_task_dependencies,
    load_selected_task_schedule_impact,
)


def on_task_list_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._request_domain_refresh()


def on_task_detail_stale(controller, task_id: str) -> None:
    """Closes the P45A/P45B-identified task_detail gap: the currently-open
    detail panel's own header/profile fields now refresh precisely when the
    selected task itself changes (TaskCreated/ProfileUpdated/HierarchyChanged/
    StatusChanged/ProgressChanged/ScheduleChanged/Removed all map to this
    target) -- previously nothing refreshed it short of leaving and
    re-entering the task."""
    if str(task_id or "") != controller._selected_task_id:
        return
    try:
        ws = controller._tasks_workspace_presenter.build_task_basic_detail_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
    except Exception:
        pass
    else:
        controller._task_list.updateSelectedTaskOnly(ws)


def on_task_schedule_stale(controller, project_id: str) -> None:
    if str(project_id or "") != controller._selected_project_id:
        return
    controller._schedule_impact_section_loaded_for_task_id = ""
    load_selected_task_schedule_impact(controller)


def on_task_assignments_for_task_stale(controller, task_id: str) -> None:
    if str(task_id or "") != controller._selected_task_id:
        return
    controller._assignments_section_loaded_for_task_id = ""
    load_selected_task_assignments(controller, force=True)


def on_task_dependencies_stale(controller, project_id: str) -> None:
    if str(project_id or "") != controller._selected_project_id:
        return
    controller._dependencies_section_loaded_for_task_id = ""
    load_selected_task_dependencies(controller)


def on_timesheet_project_stale(controller, project_id: str) -> None:
    if str(project_id or "") == controller._selected_project_id:
        controller._request_domain_refresh()


__all__ = [
    "on_task_list_stale",
    "on_task_detail_stale",
    "on_task_schedule_stale",
    "on_task_assignments_for_task_stale",
    "on_task_dependencies_stale",
    "on_timesheet_project_stale",
]
