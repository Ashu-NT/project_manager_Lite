from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsForecastViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)

from .analytics_builder import build_analytics_collection
from .cashflow_builder import build_cashflow_collection
from .commitment_builder import build_commitment_summary
from .detail_builder import build_detail_view_model
from .filtering import build_empty_state, matches_cost_type, matches_search
from .forecast_builder import build_forecast_view_model
from .ledger_builder import build_ledger_collection
from .overview_builder import build_overview
from .record_mappers import to_cost_record
from .selection import normalize_cost_type_filter, resolve_project_id, resolve_selected_cost_id


def build_workspace_state(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    selected_project_id: str | None = None,
    selected_cost_type: str = "all",
    search_text: str = "",
    selected_cost_id: str | None = None,
) -> FinancialsWorkspaceViewModel:
    project_options = tuple(
        FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_projects()
    )
    resolved_project_id = resolve_project_id(selected_project_id, project_options)
    cost_type_options = (
        FinancialsSelectorOptionViewModel(value="all", label="All categories"),
        *(
            FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_cost_types()
        ),
    )
    task_options = (
        FinancialsSelectorOptionViewModel(value="", label="Not linked to a task"),
        *(
            FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_tasks(resolved_project_id)
        ),
    )
    normalized_search = (search_text or "").strip()
    normalized_cost_type = normalize_cost_type_filter(selected_cost_type, cost_type_options)
    all_costs = desktop_api.list_cost_items(resolved_project_id)
    filtered_costs = tuple(
        cost
        for cost in all_costs
        if matches_cost_type(cost, normalized_cost_type)
        and matches_search(cost, normalized_search)
    )
    resolved_selected_cost_id = resolve_selected_cost_id(selected_cost_id, filtered_costs)
    selected_cost = next(
        (cost for cost in filtered_costs if cost.id == resolved_selected_cost_id),
        None,
    )
    snapshot = desktop_api.get_finance_snapshot(resolved_project_id)
    empty_state = build_empty_state(
        project_options=project_options,
        all_costs=all_costs,
        filtered_costs=filtered_costs,
        selected_project_id=resolved_project_id,
        search_text=normalized_search,
        selected_cost_type=normalized_cost_type,
    )
    forecast_dto = desktop_api.get_cost_forecast(resolved_project_id, method="bac_over_cpi")
    return FinancialsWorkspaceViewModel(
        overview=build_overview(
            project_options=project_options,
            selected_project_id=resolved_project_id,
            snapshot=snapshot,
            all_costs=all_costs,
            filtered_costs=filtered_costs,
        ),
        project_options=project_options,
        cost_type_options=cost_type_options,
        task_options=task_options,
        selected_project_id=resolved_project_id,
        selected_cost_type=normalized_cost_type,
        search_text=normalized_search,
        costs=FinancialsCollectionViewModel(
            title="Cost Items",
            subtitle="Manage planned, committed, and actual cost lines for the selected project.",
            empty_state=empty_state,
            items=tuple(to_cost_record(cost) for cost in filtered_costs),
        ),
        selected_cost_id=resolved_selected_cost_id,
        selected_cost_detail=build_detail_view_model(selected_cost),
        cashflow=build_cashflow_collection(snapshot),
        ledger=build_ledger_collection(snapshot),
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
        notes=tuple(snapshot.notes),
        empty_state=empty_state,
    )


def compute_forecast(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    selected_project_id: str | None,
    *,
    method: str = "bac_over_cpi",
) -> FinancialsForecastViewModel:
    normalized_method = (method or "bac_over_cpi").strip().lower()
    forecast_dto = desktop_api.get_cost_forecast(selected_project_id, method=normalized_method)
    return build_forecast_view_model(forecast_dto)
