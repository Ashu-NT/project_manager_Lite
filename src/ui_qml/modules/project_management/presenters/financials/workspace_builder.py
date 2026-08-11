from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsForecastViewModel,
    FinancialsManualActualOptionsViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)

from .analytics_builder import build_analytics_collection
from .cashflow_builder import build_cashflow_collection
from .commitment_builder import build_commitment_collection, build_commitment_summary
from .configuration_builder import build_finance_configuration_views
from .forecast_builder import build_forecast_view_model
from .ledger_builder import build_ledger_collection
from .overview_builder import build_overview
from .selection import resolve_project_id


def build_workspace_state(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    selected_project_id: str | None = None,
    budget_line_page: int = 1,
    rate_line_page: int = 1,
    planned_cost_line_page: int = 1,
    configuration_page_size: int = 50,
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
    actual_page = desktop_api.list_cost_entries(resolved_project_id, limit=50)
    commitment_page = desktop_api.list_commitments(resolved_project_id, limit=50)
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
        ledger=build_ledger_collection(actual_page),
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
        commitment_summary=build_commitment_summary(
            desktop_api.get_commitment_summary(resolved_project_id)
        ),
        commitments=build_commitment_collection(commitment_page),
        baseline_variance=tuple(
            BaselineVarianceRowViewModel(
                task_id=rec.task_id,
                task_name=rec.task_name,
                start_variance_days=rec.start_variance_days,
                finish_variance_days=rec.finish_variance_days,
                cost_variance=rec.cost_variance,
                cost_variance_label=rec.cost_variance_label,
                tone=rec.tone,
            )
            for rec in desktop_api.build_baseline_variance(resolved_project_id)
        ),
        financial_profile=configuration_views["profile"],
        budget_versions=configuration_views["budget_versions"],
        budget_lines=configuration_views["budget_lines"],
        rate_cards=configuration_views["rate_cards"],
        rate_lines=configuration_views["rate_lines"],
        planned_cost_versions=configuration_views["planned_cost_versions"],
        planned_cost_lines=configuration_views["planned_cost_lines"],
        notes=tuple(snapshot.notes),
        empty_state=empty_state,
    )
