from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
    build_project_management_financials_desktop_api,
)
from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import FinancialsWorkspaceViewModel

from .command_handler import (
    approve_actual,
    create_manual_actual,
    post_actual,
    reject_actual,
    reverse_actual,
    submit_actual,
)
from .workspace_builder import build_workspace_state
from .destination_builder import build_destination_state, build_shell_state

class ProjectFinancialsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementFinancialsDesktopApi | None = None,
        audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_financials_desktop_api()
        self._audit_api = audit_api

    def build_shell_state(
        self,
        *,
        selected_project_id: str | None = None,
    ) -> FinancialsWorkspaceViewModel:
        return build_shell_state(
            self._desktop_api,
            selected_project_id=selected_project_id,
        )

    def build_destination_state(self, **query: Any) -> FinancialsWorkspaceViewModel:
        return build_destination_state(
            self._desktop_api,
            audit_api=self._audit_api,
            **query,
        )

    def build_workspace_state(
        self,
        *,
        selected_project_id: str | None = None,
        budget_line_page: int = 1,
        rate_line_page: int = 1,
        planned_cost_line_page: int = 1,
        billing_preparation_page: int = 1,
        configuration_page_size: int = 50,
        actual_page: int = 1,
        commitment_page: int = 1,
        transaction_page_size: int = 50,
        actual_sort_key: str = "metaText",
        actual_sort_direction: str = "desc",
        commitment_sort_key: str = "metaText",
        commitment_sort_direction: str = "desc",
        selected_forecast_id: str | None = None,
        selected_change_id: str | None = None,
        selected_baseline_id: str | None = None,
    ) -> FinancialsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            selected_project_id=selected_project_id,
            budget_line_page=budget_line_page,
            rate_line_page=rate_line_page,
            planned_cost_line_page=planned_cost_line_page,
            billing_preparation_page=billing_preparation_page,
            configuration_page_size=configuration_page_size,
            actual_page=actual_page,
            commitment_page=commitment_page,
            transaction_page_size=transaction_page_size,
            actual_sort_key=actual_sort_key,
            actual_sort_direction=actual_sort_direction,
            commitment_sort_key=commitment_sort_key,
            commitment_sort_direction=commitment_sort_direction,
            selected_forecast_id=selected_forecast_id,
            selected_change_id=selected_change_id,
            selected_baseline_id=selected_baseline_id,
        )

    def create_manual_actual(self, payload: dict[str, Any]) -> None:
        create_manual_actual(self._desktop_api, payload)

    def submit_actual(self, payload: dict[str, Any]) -> None:
        submit_actual(self._desktop_api, payload)

    def approve_actual(self, payload: dict[str, Any]) -> None:
        approve_actual(self._desktop_api, payload)

    def reject_actual(self, payload: dict[str, Any]) -> None:
        reject_actual(self._desktop_api, payload)

    def post_actual(self, payload: dict[str, Any]) -> None:
        post_actual(self._desktop_api, payload)

    def reverse_actual(self, payload: dict[str, Any]) -> None:
        reverse_actual(self._desktop_api, payload)

    def export_financial_report(
        self,
        *,
        project_id: str,
        output_path: str,
        report_format: str,
        baseline_id: str | None,
    ) -> str:
        return self._desktop_api.export_financial_report(
            project_id,
            output_path,
            report_format=report_format,
            baseline_id=baseline_id,
        )

__all__ = ["ProjectFinancialsWorkspacePresenter"]
