from __future__ import annotations


def select_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip()
    if normalized == controller._selected_project_id:
        return
    controller._set_selected_project_id(normalized)
    controller._set_selected_task_id("")
    controller._set_selected_assignment_id("")
    controller._set_selected_time_period_start("")
    controller._set_selected_time_entry_id("")
    controller._task_page = 1
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
    controller._set_selected_time_period_start("")
    controller._set_selected_time_entry_id("")
    controller._set_time_section_loaded_for_task_id("")
    controller._set_collaboration_section_loaded_for_task_id("")
    controller._assignments_section_loaded_for_task_id = ""
    controller._dependencies_section_loaded_for_task_id = ""
    controller._skill_requirements_section_loaded_for_task_id = ""
    controller._schedule_impact_section_loaded_for_task_id = ""
    controller._set_schedule_impact({})


__all__ = [
    "activate_task",
    "reset_task_lazy_sections",
    "select_project",
    "select_task",
]
