from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenancePreventiveDesktopApi,
    build_maintenance_preventive_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.preventive import (
    MaintenancePreventiveWorkspaceViewModel,
)

from . import generation_command_handler as _gen
from . import plan_command_handler as _plan
from . import plan_task_command_handler as _plan_task
from . import task_step_command_handler as _step
from . import task_template_command_handler as _template
from .workspace_builder import build_workspace_state


class MaintenancePreventiveWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenancePreventiveDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_preventive_desktop_api()

    def build_workspace_state(
        self,
        *,
        queue_site_filter: str = "all",
        queue_due_state_filter: str = "all",
        queue_search_text: str = "",
        selected_queue_plan_id: str | None = None,
        plan_site_filter: str = "all",
        plan_asset_filter: str = "all",
        plan_system_filter: str = "all",
        plan_active_filter: str = "all",
        plan_status_filter: str = "all",
        plan_type_filter: str = "all",
        plan_trigger_mode_filter: str = "all",
        plan_search_text: str = "",
        selected_plan_id: str | None = None,
        selected_plan_task_id: str | None = None,
        template_active_filter: str = "all",
        template_maintenance_type_filter: str = "all",
        template_status_filter: str = "all",
        template_search_text: str = "",
        selected_task_template_id: str | None = None,
        selected_task_step_id: str | None = None,
        generation_results: list[dict[str, object]] | None = None,
    ) -> MaintenancePreventiveWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            queue_site_filter=queue_site_filter,
            queue_due_state_filter=queue_due_state_filter,
            queue_search_text=queue_search_text,
            selected_queue_plan_id=selected_queue_plan_id,
            plan_site_filter=plan_site_filter,
            plan_asset_filter=plan_asset_filter,
            plan_system_filter=plan_system_filter,
            plan_active_filter=plan_active_filter,
            plan_status_filter=plan_status_filter,
            plan_type_filter=plan_type_filter,
            plan_trigger_mode_filter=plan_trigger_mode_filter,
            plan_search_text=plan_search_text,
            selected_plan_id=selected_plan_id,
            selected_plan_task_id=selected_plan_task_id,
            template_active_filter=template_active_filter,
            template_maintenance_type_filter=template_maintenance_type_filter,
            template_status_filter=template_status_filter,
            template_search_text=template_search_text,
            selected_task_template_id=selected_task_template_id,
            selected_task_step_id=selected_task_step_id,
            generation_results=generation_results,
        )

    def create_plan(self, payload: dict) -> None:
        _plan.create_plan(self._desktop_api, payload)

    def update_plan(self, payload: dict) -> None:
        _plan.update_plan(self._desktop_api, payload)

    def toggle_plan_active(
        self,
        *,
        plan_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        _plan.toggle_plan_active(
            self._desktop_api,
            plan_id=plan_id,
            is_active=is_active,
            expected_version=expected_version,
        )

    def create_plan_task(self, payload: dict) -> None:
        _plan_task.create_plan_task(self._desktop_api, payload)

    def update_plan_task(self, payload: dict) -> None:
        _plan_task.update_plan_task(self._desktop_api, payload)

    def create_task_template(self, payload: dict) -> None:
        _template.create_task_template(self._desktop_api, payload)

    def update_task_template(self, payload: dict) -> None:
        _template.update_task_template(self._desktop_api, payload)

    def toggle_task_template_active(
        self,
        *,
        task_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        _template.toggle_task_template_active(
            self._desktop_api,
            task_template_id=task_template_id,
            is_active=is_active,
            expected_version=expected_version,
        )

    def create_task_step(self, payload: dict) -> None:
        _step.create_task_step(self._desktop_api, payload)

    def update_task_step(self, payload: dict) -> None:
        _step.update_task_step(self._desktop_api, payload)

    def toggle_task_step_active(
        self,
        *,
        task_step_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> None:
        _step.toggle_task_step_active(
            self._desktop_api,
            task_step_template_id=task_step_template_id,
            is_active=is_active,
            expected_version=expected_version,
        )

    def generate_due_work(self, *, plan_id: str) -> list[dict[str, object]]:
        return _gen.generate_due_work(self._desktop_api, plan_id=plan_id)

    def regenerate_plan_schedule(self, *, plan_id: str) -> None:
        _plan.regenerate_plan_schedule(self._desktop_api, plan_id=plan_id)


__all__ = ["MaintenancePreventiveWorkspacePresenter"]
