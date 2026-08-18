from __future__ import annotations


def select_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip()
    if normalized == controller._selected_project_id:
        return
    controller._set_selected_project_id(normalized)
    controller._set_selected_task_id("")
    controller._set_selected_assignment_id("")
    controller._set_time_resource_filter("")
    controller._set_time_page(1)
    controller._set_selected_time_entry_id("")
    controller._task_page = 1
    controller._assignments_ctrl.clearAssignmentPreview()
    controller._assignments_ctrl.clearProjectResourceUsage()
    controller._time_ctrl._set_task_time_summary(None)
    controller._time_ctrl._set_task_time_entries_page(None)
    controller.refresh()


def select_task(controller, task_id: str) -> None:
    normalized = (task_id or "").strip()
    if normalized == controller._selected_task_id:
        return
    controller._set_selected_task_id(normalized)
    reset_task_lazy_sections(controller)


def activate_task(controller, task_id: str) -> None:
    normalized = (task_id or "").strip()
    if not normalized:
        return
    controller._set_selected_task_id(normalized)
    reset_task_lazy_sections(controller)
    controller._task_list.selectTaskPreview(normalized)

    controller._set_is_loading(True)
    controller._set_error_message("")
    try:
        ws = controller._tasks_workspace_presenter.build_task_basic_detail_state(
            task_id=normalized,
            project_id=controller._selected_project_id or None,
        )
    except Exception as exc:
        controller._set_error_message(str(exc))
    else:
        controller._task_list.updateSelectedTaskOnly(ws)
        controller._set_selected_task_id(ws.selected_task_id)
    finally:
        controller._set_is_loading(False)


def reset_task_lazy_sections(controller) -> None:
    controller._set_selected_assignment_id("")
    controller._set_time_resource_filter("")
    controller._set_time_page(1)
    controller._set_selected_time_entry_id("")
    controller._set_time_section_loaded_for_task_id("")
    controller._set_collaboration_section_loaded_for_task_id("")
    controller._assignments_section_loaded_for_task_id = ""
    controller._dependencies_section_loaded_for_task_id = ""
    controller._skill_requirements_section_loaded_for_task_id = ""
    controller._schedule_impact_section_loaded_for_task_id = ""
    controller._set_schedule_impact({})
    # Switching tasks must not leave the previous task's assignment capacity
    # preview or project resource usage visible under the new task (§42).
    controller._assignments_ctrl.clearAssignmentPreview()
    controller._assignments_ctrl.clearProjectResourceUsage()
    # Nor the previous task's Time summary/entries/selected-entry -- if the
    # Time tab happens to already be the active one when the task changes,
    # the lazy loader only refetches once that tab is (re-)activated, so
    # the stale data must be cleared immediately here too (docs §44 Time
    # redesign).
    controller._time_ctrl._set_task_time_summary(None)
    controller._time_ctrl._set_task_time_entries_page(None)
    controller._time_ctrl._set_selected_time_entry({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {},
    })


__all__ = [
    "activate_task",
    "reset_task_lazy_sections",
    "select_project",
    "select_task",
]
