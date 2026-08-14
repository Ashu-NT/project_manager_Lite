from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsManualActualOptionsViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)

from .analytics_builder import build_analytics_collection
from .billing_builder import build_billing_views
from .cashflow_builder import build_cashflow_collection
from .commitment_builder import build_commitment_collection, build_commitment_summary
from .configuration_builder import build_finance_configuration_views
from .forecast_builder import build_forecast_view_model
from .ledger_builder import build_ledger_collection
from .lifecycle_builder import build_lifecycle_views
from .overview_builder import build_overview
from .selection import resolve_project_id


def build_workspace_state(
    desktop_api: ProjectManagementFinancialsDesktopApi,
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
    project_options = tuple(
        FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_projects()
    )
    resolved_project_id = resolve_project_id(selected_project_id, project_options)
    task_options = (
        FinancialsSelectorOptionViewModel(value="", label="Not linked to a task"),
        *(
            FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_tasks(resolved_project_id)
        ),
    )
    snapshot = desktop_api.get_finance_snapshot(resolved_project_id)
    normalized_actual_page = max(1, int(actual_page))
    normalized_commitment_page = max(1, int(commitment_page))
    normalized_transaction_page_size = max(1, min(int(transaction_page_size), 200))
    actual_page_result = desktop_api.list_cost_entries(
        resolved_project_id,
        offset=(normalized_actual_page - 1) * normalized_transaction_page_size,
        limit=normalized_transaction_page_size,
        sort_key=actual_sort_key,
        sort_direction=actual_sort_direction,
    )
    commitment_page_result = desktop_api.list_commitments(
        resolved_project_id,
        offset=(normalized_commitment_page - 1) * normalized_transaction_page_size,
        limit=normalized_transaction_page_size,
        sort_key=commitment_sort_key,
        sort_direction=commitment_sort_direction,
    )
    actual_options = desktop_api.get_manual_actual_options(resolved_project_id)
    empty_state = "" if resolved_project_id else "Select a project to review financials."
    forecast_dto = desktop_api.get_cost_forecast(resolved_project_id)
    configuration_views = build_finance_configuration_views(
        desktop_api.get_configuration_workspace(
            resolved_project_id,
            budget_line_page=budget_line_page,
            rate_line_page=rate_line_page,
            planned_cost_line_page=planned_cost_line_page,
            page_size=configuration_page_size,
        )
    )
    lifecycle_views = build_lifecycle_views(
        desktop_api,
        project_id=resolved_project_id,
        selected_forecast_id=selected_forecast_id,
        selected_change_id=selected_change_id,
        selected_baseline_id=selected_baseline_id,
    )
    billing_views = build_billing_views(
        desktop_api.get_billing_workspace(
            resolved_project_id,
            preparation_page=billing_preparation_page,
            page_size=configuration_page_size,
        )
    )
    return FinancialsWorkspaceViewModel(
        overview=build_overview(
            project_options=project_options,
            selected_project_id=resolved_project_id,
            snapshot=snapshot,
        ),
        project_options=project_options,
        task_options=task_options,
        manual_actual_options=FinancialsManualActualOptionsViewModel(
            currency_code=actual_options.currency_code,
            cost_codes=tuple(
                FinancialsSelectorOptionViewModel(value=item.value, label=item.label)
                for item in actual_options.cost_codes
            ),
            entry_kinds=tuple(
                FinancialsSelectorOptionViewModel(value=item.value, label=item.label)
                for item in actual_options.entry_kinds
            ),
        ),
        selected_project_id=resolved_project_id,
        cashflow=build_cashflow_collection(snapshot),
        ledger=build_ledger_collection(actual_page_result),
        actual_sort_key=actual_page_result.sort_key,
        actual_sort_direction=actual_page_result.sort_direction,
        source_analytics=build_analytics_collection(
            title="Source Breakdown",
            subtitle="Expense exposure grouped by source.",
            rows=snapshot.by_source,
        ),
        cost_type_analytics=build_analytics_collection(
            title="Cost Type Breakdown",
            subtitle="Expense exposure grouped by category.",
            rows=snapshot.by_cost_type,
        ),
        forecast=build_forecast_view_model(forecast_dto),
        selected_forecast_id=lifecycle_views["selected_forecast_id"],
        forecast_versions=lifecycle_views["forecast_versions"],
        forecast_lines=lifecycle_views["forecast_lines"],
        selected_change_id=lifecycle_views["selected_change_id"],
        financial_changes=lifecycle_views["financial_changes"],
        financial_change_impacts=lifecycle_views["financial_change_impacts"],
        commitment_summary=build_commitment_summary(
            desktop_api.get_commitment_summary(resolved_project_id)
        ),
        commitments=build_commitment_collection(commitment_page_result),
        commitment_sort_key=commitment_page_result.sort_key,
        commitment_sort_direction=commitment_page_result.sort_direction,
        baseline_variance=lifecycle_views["baseline_variance"],
        selected_baseline_id=lifecycle_views["selected_baseline_id"],
        baseline_versions=lifecycle_views["baseline_versions"],
        variance_basis=lifecycle_views["variance_basis"],
        report_basis=FinancialsDetailViewModel(
            id=resolved_project_id,
            title="Canonical Financial Report",
            status_label="Reconciled at export time" if resolved_project_id else "",
            empty_state="Select a project before exporting a financial report.",
            fields=(
                FinancialsDetailFieldViewModel(
                    "Currency basis", actual_options.currency_code or "Project currency"
                ),
                FinancialsDetailFieldViewModel(
                    "Forecast basis", forecast_dto.basis_label or "No approved forecast"
                ),
                FinancialsDetailFieldViewModel(
                    "Schedule baseline",
                    lifecycle_views["variance_basis"].title or "No selected baseline",
                ),
                FinancialsDetailFieldViewModel(
                    "Source detail",
                    "Bounded to 500 ledger rows per export page",
                    "Control totals always use the complete reconciled snapshot.",
                ),
            ) if resolved_project_id else (),
        ),
        financial_profile=configuration_views["profile"],
        budget_versions=configuration_views["budget_versions"],
        budget_lines=configuration_views["budget_lines"],
        rate_cards=configuration_views["rate_cards"],
        rate_lines=configuration_views["rate_lines"],
        planned_cost_versions=configuration_views["planned_cost_versions"],
        planned_cost_lines=configuration_views["planned_cost_lines"],
        billing_profile=billing_views["billing_profile"],
        billing_schedule=billing_views["billing_schedule"],
        billing_preparations=billing_views["billing_preparations"],
        notes=tuple(snapshot.notes),
        empty_state=empty_state,
    )
