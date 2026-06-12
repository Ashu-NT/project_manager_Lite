from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import run_mutation

from .preventive_helpers import normalize_filter, normalize_id


def apply_plan_site_filter(controller, site_id: str) -> None:
    normalized = normalize_filter(site_id)
    if normalized == controller._plan_site_filter:
        return
    controller._plan_site_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_asset_filter(controller, asset_id: str) -> None:
    normalized = normalize_filter(asset_id)
    if normalized == controller._plan_asset_filter:
        return
    controller._plan_asset_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_system_filter(controller, system_id: str) -> None:
    normalized = normalize_filter(system_id)
    if normalized == controller._plan_system_filter:
        return
    controller._plan_system_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_active_filter(controller, active_filter: str) -> None:
    normalized = normalize_filter(active_filter)
    if normalized == controller._plan_active_filter:
        return
    controller._plan_active_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_status_filter(controller, status: str) -> None:
    normalized = normalize_filter(status)
    if normalized == controller._plan_status_filter:
        return
    controller._plan_status_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_type_filter(controller, plan_type: str) -> None:
    normalized = normalize_filter(plan_type)
    if normalized == controller._plan_type_filter:
        return
    controller._plan_type_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_trigger_mode_filter(controller, trigger_mode: str) -> None:
    normalized = normalize_filter(trigger_mode)
    if normalized == controller._plan_trigger_mode_filter:
        return
    controller._plan_trigger_mode_filter = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_plan_search_text(controller, search_text: str) -> None:
    normalized = normalize_id(search_text)
    if normalized == controller._plan_search_text:
        return
    controller._plan_search_text = normalized
    controller._selected_plan_id = ""
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_select_plan(controller, plan_id: str) -> None:
    normalized = normalize_id(plan_id)
    if normalized == controller._selected_plan_id:
        return
    controller._selected_plan_id = normalized
    controller._selected_plan_task_id = ""
    controller.refresh()


def apply_select_plan_task(controller, plan_task_id: str) -> None:
    normalized = normalize_id(plan_task_id)
    if normalized == controller._selected_plan_task_id:
        return
    controller._selected_plan_task_id = normalized
    controller.refresh()


def create_plan(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.create_plan(
            dict(payload)
        ),
        success_message="Preventive plan created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_plan(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.update_plan(
            dict(payload)
        ),
        success_message="Preventive plan updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def toggle_plan_active(
    controller, plan_id: str, is_active: bool, expected_version: int
) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.toggle_plan_active(
            plan_id=plan_id,
            is_active=is_active,
            expected_version=expected_version,
        ),
        success_message="Preventive plan updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def create_plan_task(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.create_plan_task(
            dict(payload)
        ),
        success_message="Plan task created.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_plan_task(controller, payload: dict) -> dict:
    return run_mutation(
        operation=lambda: controller._preventive_workspace_presenter.update_plan_task(
            dict(payload)
        ),
        success_message="Plan task updated.",
        on_success=controller.refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )
