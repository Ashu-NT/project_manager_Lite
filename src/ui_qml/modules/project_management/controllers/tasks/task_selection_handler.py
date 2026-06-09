from __future__ import annotations

from PySide6.QtCore import QThreadPool

from .task_detail_worker import TaskDetailWorker


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
    controller._task_activation_request_id += 1
    req_id = controller._task_activation_request_id

    worker = TaskDetailWorker(
        presenter=controller._tasks_workspace_presenter,
        task_id=normalized,
        project_id=controller._selected_project_id or None,
        request_id=req_id,
    )
    worker.signals.finished.connect(controller._on_task_detail_loaded)
    worker.signals.failed.connect(controller._on_task_detail_error)
    QThreadPool.globalInstance().start(worker)


def on_task_detail_loaded(controller, data: object) -> None:
    try:
        request_id, ws = data  # type: ignore[misc]
    except (TypeError, ValueError):
        return
    if request_id != controller._task_activation_request_id:
        return  # stale result from a superseded task click
    controller._task_list.updateSelectedTaskOnly(ws)
    controller._set_selected_task_id(ws.selected_task_id)
    controller._set_is_loading(False)


def on_task_detail_error(controller, data: object) -> None:
    try:
        request_id, message = data  # type: ignore[misc]
    except (TypeError, ValueError):
        return
    if request_id != controller._task_activation_request_id:
        return
    controller._set_error_message(str(message))
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
    "on_task_detail_error",
    "on_task_detail_loaded",
    "reset_task_lazy_sections",
    "select_project",
    "select_task",
]
