from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation

from .project_lazy_section_loader import load_project_resources


def load_assignable_resources(controller) -> None:
    if not controller._selected_project_id:
        controller._set_assignable_resource_options([])
        return
    try:
        options = controller._projects_workspace_presenter.build_assignable_resource_options(
            project_id=controller._selected_project_id
        )
        controller._set_assignable_resource_options(options)
    except Exception:
        controller._set_assignable_resource_options([])


def select_project_resource(controller, project_resource_id: str) -> None:
    v = (project_resource_id or "").strip()
    if v == controller._selected_project_resource_id:
        return
    controller._selected_project_resource_id = v
    controller.selectedProjectResourceIdChanged.emit()


def assign_project_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(payload.get("resourceId", "") or "").strip()
    planned_hours = float(payload.get("plannedHours", 0) or 0)
    hourly_rate_str = str(payload.get("hourlyRate", "") or "").strip()
    hourly_rate: float | None = None
    if hourly_rate_str:
        try:
            hourly_rate = float(hourly_rate_str)
        except ValueError:
            hourly_rate = None
    return run_mutation(
        operation=lambda: controller._projects_workspace_presenter.assign_resource_to_project(
            project_id=controller._selected_project_id,
            resource_id=resource_id,
            planned_hours=planned_hours,
            hourly_rate=hourly_rate,
        ),
        success_message="Resource assigned to project.",
        on_success=lambda: on_resource_assigned(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def update_project_resource(controller, payload: dict[str, object]) -> dict[str, object]:
    pr_id = str(payload.get("projectResourceId", "") or "").strip()
    planned_hours = float(payload.get("plannedHours", 0) or 0)
    hourly_rate_str = str(payload.get("hourlyRate", "") or "").strip()
    hourly_rate: float | None = None
    if hourly_rate_str:
        try:
            hourly_rate = float(hourly_rate_str)
        except ValueError:
            hourly_rate = None
    is_active = bool(payload.get("isActive", True))
    return run_mutation(
        operation=lambda: controller._projects_workspace_presenter.update_project_resource(
            project_resource_id=pr_id,
            planned_hours=planned_hours,
            hourly_rate=hourly_rate,
            is_active=is_active,
        ),
        success_message="Resource updated.",
        on_success=lambda: on_resource_mutated(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def remove_project_resource(controller, project_resource_id: str) -> dict[str, object]:
    pr_id = (project_resource_id or "").strip()
    return run_mutation(
        operation=lambda: controller._projects_workspace_presenter.remove_project_resource(
            project_resource_id=pr_id,
        ),
        success_message="Resource removed from project.",
        on_success=lambda: on_resource_mutated(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def on_resource_assigned(controller) -> None:
    controller._project_resources_loaded_for_project_id = ""
    load_project_resources(controller)
    load_assignable_resources(controller)


def on_resource_mutated(controller) -> None:
    controller._selected_project_resource_id = ""
    controller.selectedProjectResourceIdChanged.emit()
    controller._project_resources_loaded_for_project_id = ""
    load_project_resources(controller)


__all__ = [
    "assign_project_resource",
    "load_assignable_resources",
    "on_resource_assigned",
    "on_resource_mutated",
    "remove_project_resource",
    "select_project_resource",
    "update_project_resource",
]
