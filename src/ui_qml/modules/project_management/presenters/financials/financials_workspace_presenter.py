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
    create_cost_code,
    create_manual_actual,
    post_actual,
    reject_actual,
    reverse_actual,
    submit_actual,
)
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

    def create_manual_actual(self, payload: dict[str, Any]) -> None:
        create_manual_actual(self._desktop_api, payload)

    def create_cost_code(self, payload: dict[str, Any]) -> None:
        create_cost_code(self._desktop_api, payload)

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
