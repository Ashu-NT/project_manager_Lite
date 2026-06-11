from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import run_mutation

from .preventive_helpers import normalize_filter, normalize_id


def apply_template_active_filter(controller, active_filter: str) -> None:
    normalized = normalize_filter(active_filter)
    if normalized == controller._template_active_filter:
        return
    controller._template_active_filter = normalized
    controller._selected_task_template_id = ""
    controller._selected_task_step_id = ""
    controller.refresh()


def apply_template_maintenance_type_filter(
    controller, maintenance_type: str
) -> None:
    normalized = normalize_filter(maintenance_type)
    if normalized == controller._template_maintenance_type_filter:
        return
    controller._template_maintenance_type_filter = normalized
    controller._selected_task_template_id = ""
    controller._selected_task_step_id = ""
    controller.refresh()


def apply_template_status_filter(controller, template_status: str) -> None:
    normalized = normalize_filter(template_status)
    if normalized == controller._template_status_filter:
        return
    controller._template_status_filter = normalized
    controller._selected_task_template_id = ""
    controller._selected_task_step_id = ""
    controller.refresh()


def apply_template_search_text(controller, search_text: str) -> None:
    normalized = normalize_id(search_text)
    if normalized == controller._template_search_text:
        return
    controller._template_search_text = normalized
    controller._selected_task_template_id = ""
    controller._selected_task_step_id = ""
    controller.refresh()


def apply_select_task_template(controller, task_template_id: str) -> None:
    normalized = normalize_id(task_template_id)
    if normalized == controller._selected_task_template_id:
        return
    controller._selected_task_template_id = normalized
    controller._selected_task_step_id = ""
    controller.refresh()


def apply_select_task_step(controller, task_step_template_id: str) -> None:
    normalized = normalize_id(task_step_template_id)
    if normalized == controller._selected_task_step_id:
        return
    controller._selected_task_step_id = normalized
    controller.refresh()


def create_task_template(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.create_task_template(
            dict(payload)
        ),
        success_message="Task template created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_task_template(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.update_task_template(
            dict(payload)
        ),
        success_message="Task template updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_task_template_active(
    controller, task_template_id: str, is_active: bool, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.toggle_task_template_active(
            task_template_id=task_template_id,
            is_active=is_active,
            expected_version=expected_version,
        ),
        success_message="Task template updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def create_task_step(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.create_task_step(
            dict(payload)
        ),
        success_message="Task step created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_task_step(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.update_task_step(
            dict(payload)
        ),
        success_message="Task step updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_task_step_active(
    controller, task_step_template_id: str, is_active: bool, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.toggle_task_step_active(
            task_step_template_id=task_step_template_id,
            is_active=is_active,
            expected_version=expected_version,
        ),
        success_message="Task step updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )
