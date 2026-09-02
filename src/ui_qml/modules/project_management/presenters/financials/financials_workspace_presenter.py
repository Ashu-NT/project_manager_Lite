from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
    build_project_management_financials_desktop_api,
)
from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.ui_qml.modules.project_management.view_models.financials import FinancialsWorkspaceViewModel

from .command_handler import (
    add_budget_line,
    add_financial_change_impact,
    approve_actual,
    close_budget,
    create_budget_successor,
    create_budget_version,
    create_cost_code,
    create_manual_actual,
    create_financial_change,
    decide_budget_approval,
    decide_forecast_approval,
    decide_financial_change_approval,
    delete_budget,
    delete_budget_line,
    generate_forecast,
    post_actual,
    remove_financial_change_impact,
    reject_actual,
    reverse_actual,
    submit_actual,
    submit_budget,
    submit_forecast,
    submit_financial_change,
    request_budget_approval,
    request_forecast_approval,
    update_budget,
    update_budget_line,
    update_financial_change,
    update_financial_change_impact,
)
from .destination_builder import build_destination_state, build_shell_state

class ProjectFinancialsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementFinancialsDesktopApi | None = None,
        audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
        approval_api: PlatformApprovalDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_financials_desktop_api()
        self._audit_api = audit_api
        self._approval_api = approval_api

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

    def active_scope_ids(self) -> tuple[str, str]:
        return self._desktop_api.active_scope_ids()

    def search_finance_projects(self, **query: Any):
        return self._desktop_api.search_finance_projects(**query)

    def resolve_finance_project(self, project_id: str):
        return self._desktop_api.resolve_finance_project(project_id)

    def search_manual_actual_projects(self, **query: Any):
        return self._desktop_api.search_manual_actual_projects(**query)

    def resolve_manual_actual_project(self, project_id: str):
        return self._desktop_api.resolve_manual_actual_project(project_id)

    def search_manual_actual_tasks(self, project_id: str, **query: Any):
        return self._desktop_api.search_manual_actual_tasks(project_id, **query)

    def resolve_manual_actual_task(self, project_id: str, task_id: str):
        return self._desktop_api.resolve_manual_actual_task(project_id, task_id)

    def search_manual_actual_cost_codes(self, project_id: str, **query: Any):
        return self._desktop_api.search_manual_actual_cost_codes(project_id, **query)

    def resolve_manual_actual_cost_code(
        self, project_id: str, cost_code_id: str, **query: Any
    ):
        return self._desktop_api.resolve_manual_actual_cost_code(
            project_id, cost_code_id, **query
        )

    def get_manual_actual_defaults(self, project_id: str):
        return self._desktop_api.get_manual_actual_defaults(project_id)

    def search_budget_tasks(self, project_id: str, **query: Any):
        return self._desktop_api.search_budget_tasks(project_id, **query)

    def resolve_budget_task(self, project_id: str, task_id: str):
        return self._desktop_api.resolve_budget_task(project_id, task_id)

    def search_budget_cost_codes(self, project_id: str, **query: Any):
        return self._desktop_api.search_budget_cost_codes(project_id, **query)

    def resolve_budget_cost_code(self, project_id: str, cost_code_id: str):
        return self._desktop_api.resolve_budget_cost_code(project_id, cost_code_id)

    def search_forecast_tasks(self, project_id: str, **query: Any):
        return self._desktop_api.search_forecast_tasks(project_id, **query)

    def search_forecast_cost_codes(self, project_id: str, **query: Any):
        return self._desktop_api.search_forecast_cost_codes(project_id, **query)

    def search_forecast_risks(self, project_id: str, **query: Any):
        return self._desktop_api.search_forecast_risks(project_id, **query)

    def create_budget_version(self, project_id: str, name: str, currency: str):
        return create_budget_version(self._desktop_api, project_id, name, currency)

    def create_budget_successor(self, predecessor_id: str, name: str):
        return create_budget_successor(self._desktop_api, predecessor_id, name)

    def update_budget(self, budget_id: str, version: int, name: str, notes: str):
        return update_budget(self._desktop_api, budget_id, version, name, notes)

    def delete_budget(self, budget_id: str, version: int) -> None:
        delete_budget(self._desktop_api, budget_id, version)

    def add_budget_line(self, *args):
        return add_budget_line(self._desktop_api, *args)

    def update_budget_line(self, *args):
        return update_budget_line(self._desktop_api, *args)

    def delete_budget_line(self, line_id: str, line_version: int, parent_version: int):
        delete_budget_line(self._desktop_api, line_id, line_version, parent_version)

    def submit_budget(self, budget_id: str, version: int, notes: str):
        return submit_budget(self._desktop_api, budget_id, version, notes)

    def request_budget_approval(self, budget_id: str, version: int, notes: str):
        return request_budget_approval(self._desktop_api, budget_id, version, notes)

    def decide_budget_approval(self, request_id: str, approve: bool, note: str) -> None:
        decide_budget_approval(
            self._approval_api, request_id, approve=approve, note=note
        )

    def close_budget(self, budget_id: str, version: int, notes: str):
        return close_budget(self._desktop_api, budget_id, version, notes)

    def generate_forecast(self, payload: dict[str, Any]):
        return generate_forecast(self._desktop_api, payload)

    def submit_forecast(self, forecast_id: str, version: int, notes: str):
        return submit_forecast(self._desktop_api, forecast_id, version, notes)

    def request_forecast_approval(
        self, forecast_id: str, version: int, notes: str
    ):
        return request_forecast_approval(
            self._desktop_api, forecast_id, version, notes
        )

    def decide_forecast_approval(
        self, request_id: str, approve: bool, note: str
    ) -> None:
        decide_forecast_approval(
            self._approval_api, request_id, approve=approve, note=note
        )

    def create_financial_change(self, payload: dict[str, Any]):
        return create_financial_change(self._desktop_api, payload)

    def update_financial_change(self, payload: dict[str, Any]):
        return update_financial_change(self._desktop_api, payload)

    def add_financial_change_impact(self, payload: dict[str, Any]):
        return add_financial_change_impact(self._desktop_api, payload)

    def update_financial_change_impact(self, payload: dict[str, Any]):
        return update_financial_change_impact(self._desktop_api, payload)

    def remove_financial_change_impact(self, payload: dict[str, Any]):
        return remove_financial_change_impact(self._desktop_api, payload)

    def submit_financial_change(self, payload: dict[str, Any]):
        return submit_financial_change(self._desktop_api, payload)

    def decide_financial_change_approval(
        self, request_id: str, approve: bool, note: str
    ) -> None:
        decide_financial_change_approval(
            self._approval_api, request_id, approve=approve, note=note
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
