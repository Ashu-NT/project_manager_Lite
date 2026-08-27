from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsManualActualOptionsViewModel,
    FinancialsOverviewViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)

from .analytics_builder import build_analytics_collection
from .audit_builder import build_finance_audit_collection
from .billing_builder import build_billing_views
from .cashflow_builder import build_cashflow_collection
from .commitment_builder import build_commitment_collection, build_commitment_summary
from .configuration_builder import build_finance_configuration_views
from .forecast_builder import build_forecast_view_model
from .ledger_builder import build_ledger_collection
from .lifecycle_builder import (
    build_change_lifecycle_views,
    build_forecast_lifecycle_views,
    build_variance_views,
)
from .overview_builder import build_overview
from .selection import resolve_project_id


FINANCE_DESTINATIONS = (
    "overview",
    "planning",
    "costs",
    "performance",
    "commercial",
    "controls",
)

FINANCE_SUBSECTIONS = {
    "overview": ("summary",),
    "planning": ("budgets", "planned_costs", "forecast"),
    "costs": ("actuals", "commitments", "rates"),
    "performance": ("variance", "cost_phasing", "reports"),
    "commercial": ("billing", "profitability", "accounting"),
    "controls": ("setup", "changes", "activity"),
}


def normalize_destination(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in FINANCE_DESTINATIONS else "overview"


def normalize_subsection(destination: str, value: str | None) -> str:
    allowed = FINANCE_SUBSECTIONS[destination]
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else allowed[0]


def _empty_overview() -> FinancialsOverviewViewModel:
    return FinancialsOverviewViewModel(
        title="Financials",
        subtitle="Select a project to review project financial control.",
        metrics=(),
    )


def _base_state(*, selected_project_id: str = "") -> FinancialsWorkspaceViewModel:
    return FinancialsWorkspaceViewModel(
        overview=_empty_overview(),
        selected_project_id=selected_project_id,
        empty_state=(
            "" if selected_project_id else "Select a project to review financials."
        ),
    )


def build_shell_state(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    selected_project_id: str | None = None,
) -> FinancialsWorkspaceViewModel:
    project_options = tuple(
        FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_projects()
    )
    resolved_project_id = resolve_project_id(selected_project_id, project_options)
    return FinancialsWorkspaceViewModel(
        overview=_empty_overview(),
        project_options=project_options,
        selected_project_id=resolved_project_id,
        empty_state=(
            "" if resolved_project_id else "Select a project to review financials."
        ),
    )


def build_destination_state(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
    destination: str,
    subsection: str | None,
    selected_project_id: str,
    selected_project_label: str = "",
    budget_line_page: int = 1,
    budget_version_page: int = 1,
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
    selected_budget_id: str | None = None,
    budget_version_sort_key: str = "revision",
    budget_version_sort_direction: str = "desc",
    budget_line_sort_key: str = "metaText",
    budget_line_sort_direction: str = "desc",
    selected_planned_cost_version_id: str | None = None,
    planned_cost_version_page: int = 1,
    planned_cost_version_sort_key: str = "revision",
    planned_cost_version_sort_direction: str = "desc",
    planned_cost_line_sort_key: str = "title",
    planned_cost_line_sort_direction: str = "asc",
    selected_change_id: str | None = None,
    selected_baseline_id: str | None = None,
) -> FinancialsWorkspaceViewModel:
    destination = normalize_destination(destination)
    subsection = normalize_subsection(destination, subsection)
    project_id = str(selected_project_id or "").strip()
    state = _base_state(selected_project_id=project_id)
    if not project_id:
        return state

    if destination == "overview":
        overview = desktop_api.get_finance_overview(project_id)
        return FinancialsWorkspaceViewModel(
            overview=build_overview(
                project_options=(),
                selected_project_id=project_id,
                selected_project_label=selected_project_label,
                snapshot=overview,
            ),
            selected_project_id=project_id,
        )

    if destination == "planning":
        if subsection in {"budgets", "planned_costs"}:
            configuration = (
                desktop_api.get_budget_workspace(
                    project_id,
                    selected_budget_id=selected_budget_id or "",
                    version_page=budget_version_page,
                    line_page=budget_line_page,
                    page_size=configuration_page_size,
                    version_sort_key=budget_version_sort_key,
                    version_sort_direction=budget_version_sort_direction,
                    line_sort_key=budget_line_sort_key,
                    line_sort_direction=budget_line_sort_direction,
                )
                if subsection == "budgets"
                else desktop_api.get_planned_cost_workspace(
                    project_id,
                    selected_version_id=selected_planned_cost_version_id or "",
                    version_page=planned_cost_version_page,
                    line_page=planned_cost_line_page,
                    page_size=configuration_page_size,
                    version_sort_key=planned_cost_version_sort_key,
                    version_sort_direction=planned_cost_version_sort_direction,
                    line_sort_key=planned_cost_line_sort_key,
                    line_sort_direction=planned_cost_line_sort_direction,
                )
            )
            views = build_finance_configuration_views(configuration)
            if subsection == "budgets":
                return FinancialsWorkspaceViewModel(
                    overview=state.overview,
                    selected_project_id=project_id,
                    selected_budget_id=views["selected_budget_id"],
                    budget_versions=views["budget_versions"],
                    budget_lines=views["budget_lines"],
                    budget_version_sort_key=views["budget_version_sort_key"],
                    budget_version_sort_direction=views["budget_version_sort_direction"],
                    budget_line_sort_key=views["budget_line_sort_key"],
                    budget_line_sort_direction=views["budget_line_sort_direction"],
                )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                selected_planned_cost_version_id=views[
                    "selected_planned_cost_version_id"
                ],
                planned_cost_versions=views["planned_cost_versions"],
                planned_cost_lines=views["planned_cost_lines"],
                planned_cost_version_sort_key=views[
                    "planned_cost_version_sort_key"
                ],
                planned_cost_version_sort_direction=views[
                    "planned_cost_version_sort_direction"
                ],
                planned_cost_line_sort_key=views["planned_cost_line_sort_key"],
                planned_cost_line_sort_direction=views[
                    "planned_cost_line_sort_direction"
                ],
            )
        forecast = desktop_api.get_cost_forecast(project_id)
        lifecycle = build_forecast_lifecycle_views(
            desktop_api,
            project_id=project_id,
            selected_forecast_id=selected_forecast_id,
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            forecast=build_forecast_view_model(forecast),
            selected_forecast_id=lifecycle["selected_forecast_id"],
            forecast_versions=lifecycle["forecast_versions"],
            forecast_lines=lifecycle["forecast_lines"],
        )

    if destination == "costs":
        if subsection == "actuals":
            page_size = max(1, min(int(transaction_page_size), 200))
            page = max(1, int(actual_page))
            result = desktop_api.list_cost_entries(
                project_id,
                offset=(page - 1) * page_size,
                limit=page_size,
                sort_key=actual_sort_key,
                sort_direction=actual_sort_direction,
            )
            options = desktop_api.get_manual_actual_options(project_id)
            tasks = (
                FinancialsSelectorOptionViewModel(
                    value="",
                    label="Not linked to a task",
                ),
                *(
                    FinancialsSelectorOptionViewModel(
                        value=item.value,
                        label=item.label,
                    )
                    for item in desktop_api.list_tasks(project_id)
                ),
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                task_options=tasks,
                manual_actual_options=FinancialsManualActualOptionsViewModel(
                    currency_code=options.currency_code,
                    cost_codes=tuple(
                        FinancialsSelectorOptionViewModel(
                            value=item.value,
                            label=item.label,
                        )
                        for item in options.cost_codes
                    ),
                    entry_kinds=tuple(
                        FinancialsSelectorOptionViewModel(
                            value=item.value,
                            label=item.label,
                        )
                        for item in options.entry_kinds
                    ),
                ),
                ledger=build_ledger_collection(result),
                actual_sort_key=result.sort_key,
                actual_sort_direction=result.sort_direction,
            )
        if subsection == "commitments":
            page_size = max(1, min(int(transaction_page_size), 200))
            page = max(1, int(commitment_page))
            result = desktop_api.list_commitments(
                project_id,
                offset=(page - 1) * page_size,
                limit=page_size,
                sort_key=commitment_sort_key,
                sort_direction=commitment_sort_direction,
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                commitment_summary=build_commitment_summary(
                    desktop_api.get_commitment_summary(project_id)
                ),
                commitments=build_commitment_collection(result),
                commitment_sort_key=result.sort_key,
                commitment_sort_direction=result.sort_direction,
            )
        configuration = desktop_api.get_configuration_workspace(
            project_id,
            rate_line_page=rate_line_page,
            page_size=configuration_page_size,
            include_profile_details=False,
            include_budgets=False,
            include_rates=True,
            include_planned_costs=False,
        )
        views = build_finance_configuration_views(configuration)
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            rate_cards=views["rate_cards"],
            rate_lines=views["rate_lines"],
        )

    if destination == "performance":
        if subsection == "variance":
            variance = build_variance_views(
                desktop_api,
                project_id=project_id,
                selected_baseline_id=selected_baseline_id,
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                selected_baseline_id=variance["selected_baseline_id"],
                baseline_versions=variance["baseline_versions"],
                baseline_variance=variance["baseline_variance"],
                variance_basis=variance["variance_basis"],
            )
        snapshot = desktop_api.get_finance_snapshot(project_id)
        if subsection == "cost_phasing":
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                cashflow=build_cashflow_collection(snapshot),
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
                notes=tuple(snapshot.notes),
            )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            report_basis=_build_report_basis(project_id, snapshot),
        )

    if destination == "commercial":
        if subsection == "profitability":
            projection = desktop_api.get_commercial_projection(project_id)
            fields = (
                FinancialsDetailFieldViewModel(
                    "Contract value",
                    f"{projection.contract_value or 'Not configured'} {projection.project_currency}".strip(),
                ),
                FinancialsDetailFieldViewModel(
                    "Billable amount",
                    f"{projection.billable_amount} {projection.project_currency}".strip(),
                ),
                FinancialsDetailFieldViewModel(
                    "Projected commercial revenue at completion",
                    (
                        f"{projection.forecast_revenue_at_completion} {projection.project_currency}".strip()
                        if projection.forecast_revenue_at_completion
                        else "Restricted or unavailable"
                    ),
                    projection.revenue_basis,
                ),
                FinancialsDetailFieldViewModel(
                    "Projected commercial margin",
                    (
                        f"{projection.projected_margin_amount} {projection.project_currency}"
                        if projection.projected_margin_amount
                        else "Restricted or unavailable"
                    ),
                    (
                        f"{projection.projected_margin_percent}%"
                        if projection.projected_margin_percent
                        else ""
                    ),
                ),
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                commercial_projection=FinancialsDetailViewModel(
                    id=project_id,
                    title="Projected Commercial Revenue/Margin",
                    status_label=(
                        "Profitability detail available"
                        if projection.profitability_detail_included
                        else "Profitability detail restricted"
                    ),
                    subtitle=(
                        "Managerial projection only; Accounting remains authoritative "
                        "for invoices, receivables, payments, and statutory outcomes."
                    ),
                    fields=fields,
                ),
            )
        billing = build_billing_views(
            desktop_api.get_billing_workspace(
                project_id,
                preparation_page=billing_preparation_page,
                page_size=configuration_page_size,
            )
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            billing_profile=billing["billing_profile"],
            billing_schedule=billing["billing_schedule"],
            billing_preparations=billing["billing_preparations"],
        )

    if subsection == "setup":
        configuration = desktop_api.get_configuration_workspace(
            project_id,
            page_size=configuration_page_size,
            include_profile_details=True,
            include_budgets=False,
            include_rates=False,
            include_planned_costs=False,
        )
        views = build_finance_configuration_views(configuration)
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            financial_profile=views["profile"],
        )
    if subsection == "changes":
        changes = build_change_lifecycle_views(
            desktop_api,
            project_id=project_id,
            selected_change_id=selected_change_id,
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            selected_change_id=changes["selected_change_id"],
            financial_changes=changes["financial_changes"],
            financial_change_impacts=changes["financial_change_impacts"],
        )
    return FinancialsWorkspaceViewModel(
        overview=state.overview,
        selected_project_id=project_id,
        activity=build_finance_audit_collection(
            audit_api,
            project_id=project_id,
            limit=100,
        ),
    )


def _build_report_basis(project_id: str, snapshot) -> FinancialsDetailViewModel:
    return FinancialsDetailViewModel(
        id=project_id,
        title="Canonical Financial Report",
        status_label="Reconciled at export time",
        empty_state="Select a project before exporting a financial report.",
        fields=(
            FinancialsDetailFieldViewModel(
                "Currency basis",
                snapshot.project_currency or "Project currency",
            ),
            FinancialsDetailFieldViewModel(
                "Forecast basis",
                (
                    f"Revision {snapshot.approved_forecast_revision}"
                    if snapshot.approved_forecast_revision is not None
                    else "No approved forecast"
                ),
            ),
            FinancialsDetailFieldViewModel(
                "As-of basis",
                snapshot.as_of.isoformat() if snapshot.as_of else "Current",
            ),
            FinancialsDetailFieldViewModel(
                "Source detail",
                "Bounded export pages with complete reconciled control totals.",
            ),
        ),
    )


__all__ = [
    "FINANCE_DESTINATIONS",
    "FINANCE_SUBSECTIONS",
    "build_destination_state",
    "build_shell_state",
    "normalize_destination",
    "normalize_subsection",
]
