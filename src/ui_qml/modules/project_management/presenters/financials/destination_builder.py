from __future__ import annotations

import calendar
from datetime import date

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsManualActualDefaultsViewModel,
    FinancialsOverviewViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)

from .audit_builder import build_finance_audit_collection
from .billing_workspace_builder import (
    build_accounting_status_collection,
    build_billing_workspace_views,
)
from .commitment_builder import build_commitment_collection, build_commitment_summary
from .configuration_builder import build_finance_configuration_views
from .change_workspace_builder import build_change_workspace_views
from .forecast_workspace_builder import build_forecast_workspace_views
from .rate_workspace_builder import build_rate_workspace_views
from .ledger_builder import build_ledger_collection
from .performance_builder import (
    build_cost_phasing_views,
    build_evm_views,
    build_reports_views,
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
    "performance": ("evm", "variance", "cost_phasing", "reports"),
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
    page = desktop_api.search_finance_projects(page=1, page_size=25)
    project_options = tuple(
        FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
        for option in page.items
    )
    requested_id = str(selected_project_id or "").strip()
    if requested_id and all(option.value != requested_id for option in project_options):
        selected = desktop_api.resolve_finance_project(requested_id)
        if selected is not None:
            project_options = (
                FinancialsSelectorOptionViewModel(
                    value=selected.value, label=selected.label
                ),
                *project_options,
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
    rate_card_page: int = 1,
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
    forecast_version_page: int = 1,
    forecast_line_page: int = 1,
    forecast_version_sort_key: str = "revision",
    forecast_version_sort_direction: str = "desc",
    forecast_line_sort_key: str = "title",
    forecast_line_sort_direction: str = "asc",
    forecast_version_search: str = "",
    forecast_version_status: str = "",
    forecast_generation_mode: str = "",
    forecast_line_search: str = "",
    forecast_line_source_type: str = "",
    selected_rate_card_id: str | None = None,
    rate_card_sort_key: str = "title",
    rate_card_sort_direction: str = "asc",
    rate_line_sort_key: str = "title",
    rate_line_sort_direction: str = "asc",
    rate_card_search: str = "",
    rate_card_scope: str = "",
    rate_card_status: str = "",
    rate_line_search: str = "",
    rate_line_rate_type: str = "",
    rate_line_status: str = "",
    rate_line_effective_status: str = "",
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
    change_page: int = 1,
    impact_page: int = 1,
    change_sort_key: str = "metaText",
    change_sort_direction: str = "desc",
    impact_sort_key: str = "metaText",
    impact_sort_direction: str = "asc",
    change_search: str = "",
    change_status: str = "",
    change_approval_status: str = "",
    change_applied_state: str = "",
    impact_search: str = "",
    impact_type: str = "",
    impact_applied_state: str = "",
    selected_billing_preparation_id: str | None = None,
    billing_schedule_page: int = 1,
    billing_line_page: int = 1,
    billing_schedule_sort_key: str = "supportingText",
    billing_schedule_sort_direction: str = "asc",
    billing_preparation_sort_key: str = "metaText",
    billing_preparation_sort_direction: str = "desc",
    billing_line_sort_key: str = "metaText",
    billing_line_sort_direction: str = "asc",
    billing_schedule_search: str = "",
    billing_schedule_status: str = "",
    billing_schedule_source_state: str = "",
    billing_preparation_search: str = "",
    billing_preparation_status: str = "",
    billing_preparation_method: str = "",
    billing_preparation_approval_status: str = "",
    billing_preparation_delivery_state: str = "",
    billing_preparation_correction_state: str = "",
    billing_line_search: str = "",
    billing_line_source_type: str = "",
    billing_line_source_state: str = "",
    selected_baseline_id: str | None = None,
    performance_as_of_date: date | None = None,
    cost_phasing_date_from: date | None = None,
    cost_phasing_date_to: date | None = None,
    cost_phasing_granularity: str = "month",
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
                    show_create_budget_version=views["show_create_budget_version"],
                    can_create_budget_version=views["can_create_budget_version"],
                    create_budget_version_disabled_reason=views[
                        "create_budget_version_disabled_reason"
                    ],
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
        forecast = desktop_api.get_forecast_workspace(
            project_id,
            selected_forecast_id=selected_forecast_id or "",
            version_page=forecast_version_page,
            line_page=forecast_line_page,
            page_size=configuration_page_size,
            version_sort_key=forecast_version_sort_key,
            version_sort_direction=forecast_version_sort_direction,
            line_sort_key=forecast_line_sort_key,
            line_sort_direction=forecast_line_sort_direction,
            version_search=forecast_version_search,
            version_status=forecast_version_status,
            generation_mode=forecast_generation_mode,
            line_search=forecast_line_search,
            line_source_type=forecast_line_source_type,
        )
        views = build_forecast_workspace_views(forecast)
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            selected_forecast_id=views["selected_forecast_id"],
            selected_forecast=views["selected_forecast"],
            forecast_versions=views["forecast_versions"],
            forecast_lines=views["forecast_lines"],
            forecast_version_sort_key=views["forecast_version_sort_key"],
            forecast_version_sort_direction=views["forecast_version_sort_direction"],
            forecast_line_sort_key=views["forecast_line_sort_key"],
            forecast_line_sort_direction=views["forecast_line_sort_direction"],
            forecast_version_search=views["forecast_version_search"],
            forecast_version_status=views["forecast_version_status"],
            forecast_generation_mode=views["forecast_generation_mode"],
            forecast_line_search=views["forecast_line_search"],
            forecast_line_source_type=views["forecast_line_source_type"],
            show_generate_forecast=views["show_generate_forecast"],
            can_generate_forecast=views["can_generate_forecast"],
            generate_forecast_disabled_reason=views[
                "generate_forecast_disabled_reason"
            ],
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
            options = desktop_api.get_manual_actual_defaults(project_id)
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                manual_actual_defaults=FinancialsManualActualDefaultsViewModel(
                    currency_code=options.currency_code,
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
        rates = desktop_api.get_rate_workspace(
            project_id,
            selected_rate_card_id=selected_rate_card_id or "",
            card_page=rate_card_page,
            line_page=rate_line_page,
            page_size=configuration_page_size,
            card_sort_key=rate_card_sort_key,
            card_sort_direction=rate_card_sort_direction,
            line_sort_key=rate_line_sort_key,
            line_sort_direction=rate_line_sort_direction,
            card_search=rate_card_search,
            card_scope=rate_card_scope,
            card_status=rate_card_status,
            line_search=rate_line_search,
            line_rate_type=rate_line_rate_type,
            line_status=rate_line_status,
            line_effective_status=rate_line_effective_status,
        )
        views = build_rate_workspace_views(rates)
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            rate_cards=views["rate_cards"],
            rate_lines=views["rate_lines"],
            selected_rate_card_id=views["selected_rate_card_id"],
            selected_rate_card=views["selected_rate_card"],
            rate_card_sort_key=views["rate_card_sort_key"],
            rate_card_sort_direction=views["rate_card_sort_direction"],
            rate_line_sort_key=views["rate_line_sort_key"],
            rate_line_sort_direction=views["rate_line_sort_direction"],
            rate_card_search=views["rate_card_search"],
            rate_card_scope=views["rate_card_scope"],
            rate_card_status=views["rate_card_status"],
            rate_line_search=views["rate_line_search"],
            rate_line_rate_type=views["rate_line_rate_type"],
            rate_line_status=views["rate_line_status"],
            rate_line_effective_status=views["rate_line_effective_status"],
        )

    if destination == "performance":
        as_of_date = performance_as_of_date or date.today()
        if subsection == "evm":
            views = build_evm_views(
                desktop_api.get_performance_evm(
                    project_id,
                    as_of_date=as_of_date,
                    baseline_id=selected_baseline_id,
                )
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                evm_basis=views["evm_basis"],
                evm_metrics=views["evm_metrics"],
            )
        if subsection == "variance":
            variance = build_variance_views(
                desktop_api.get_performance_variance(
                    project_id,
                    as_of_date=as_of_date,
                    selected_baseline_id=selected_baseline_id,
                )
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                variance_metrics=variance["variance_metrics"],
                selected_baseline_id=variance["selected_baseline_id"],
                baseline_versions=variance["baseline_versions"],
                baseline_variance=variance["baseline_variance"],
                variance_basis=variance["variance_basis"],
            )
        if subsection == "cost_phasing":
            range_to = cost_phasing_date_to or as_of_date
            range_from = cost_phasing_date_from or _months_before(range_to, 11)
            views = build_cost_phasing_views(
                desktop_api.get_cost_phasing(
                    project_id,
                    date_from=range_from,
                    date_to=range_to,
                    granularity=cost_phasing_granularity,
                )
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                cost_phasing=views["cost_phasing"],
                cost_phasing_basis=views["cost_phasing_basis"],
            )
        views = build_reports_views(
            desktop_api.get_performance_reports(project_id, as_of_date=as_of_date)
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            report_basis=views["report_basis"],
            report_definitions=views["report_definitions"],
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
        if subsection == "accounting":
            accounting = desktop_api.get_accounting_statuses(
                project_id,
                page=billing_preparation_page,
                page_size=configuration_page_size,
                sort_key=billing_preparation_sort_key,
                sort_direction=billing_preparation_sort_direction,
                search=billing_preparation_search,
            )
            return FinancialsWorkspaceViewModel(
                overview=state.overview,
                selected_project_id=project_id,
                billing_preparations=build_accounting_status_collection(accounting),
                billing_preparation_sort_key=accounting.sort_key,
                billing_preparation_sort_direction=accounting.sort_direction,
                billing_preparation_search=billing_preparation_search,
            )
        billing = build_billing_workspace_views(
            desktop_api.get_billing_read_workspace(
                project_id,
                selected_preparation_id=selected_billing_preparation_id or "",
                schedule_page=billing_schedule_page,
                preparation_page=billing_preparation_page,
                line_page=billing_line_page,
                page_size=configuration_page_size,
                schedule_sort_key=billing_schedule_sort_key,
                schedule_sort_direction=billing_schedule_sort_direction,
                preparation_sort_key=billing_preparation_sort_key,
                preparation_sort_direction=billing_preparation_sort_direction,
                line_sort_key=billing_line_sort_key,
                line_sort_direction=billing_line_sort_direction,
                schedule_search=billing_schedule_search,
                schedule_status=billing_schedule_status,
                schedule_source_state=billing_schedule_source_state,
                preparation_search=billing_preparation_search,
                preparation_status=billing_preparation_status,
                preparation_method=billing_preparation_method,
                preparation_approval_status=billing_preparation_approval_status,
                preparation_delivery_state=billing_preparation_delivery_state,
                preparation_correction_state=billing_preparation_correction_state,
                line_search=billing_line_search,
                line_source_type=billing_line_source_type,
                line_source_state=billing_line_source_state,
            )
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            billing_profile=billing["billing_profile"],
            billing_schedule=billing["billing_schedule"],
            billing_preparations=billing["billing_preparations"],
            selected_billing_preparation_id=billing["selected_billing_preparation_id"],
            selected_billing_preparation=billing["selected_billing_preparation"],
            billing_preparation_lines=billing["billing_preparation_lines"],
            billing_schedule_sort_key=billing["billing_schedule_sort_key"],
            billing_schedule_sort_direction=billing["billing_schedule_sort_direction"],
            billing_preparation_sort_key=billing["billing_preparation_sort_key"],
            billing_preparation_sort_direction=billing["billing_preparation_sort_direction"],
            billing_line_sort_key=billing["billing_line_sort_key"],
            billing_line_sort_direction=billing["billing_line_sort_direction"],
            billing_schedule_search=billing["billing_schedule_search"],
            billing_schedule_status=billing["billing_schedule_status"],
            billing_schedule_source_state=billing["billing_schedule_source_state"],
            billing_preparation_search=billing["billing_preparation_search"],
            billing_preparation_status=billing["billing_preparation_status"],
            billing_preparation_method=billing["billing_preparation_method"],
            billing_preparation_approval_status=billing["billing_preparation_approval_status"],
            billing_preparation_delivery_state=billing["billing_preparation_delivery_state"],
            billing_preparation_correction_state=billing["billing_preparation_correction_state"],
            billing_line_search=billing["billing_line_search"],
            billing_line_source_type=billing["billing_line_source_type"],
            billing_line_source_state=billing["billing_line_source_state"],
        )

    if subsection == "setup":
        configuration = desktop_api.get_financial_setup_workspace(project_id)
        views = build_finance_configuration_views(configuration)
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            financial_profile=views["profile"],
        )
    if subsection == "changes":
        changes = build_change_workspace_views(
            desktop_api.get_change_workspace(
                project_id,
                selected_change_id=selected_change_id or "",
                change_page=change_page,
                impact_page=impact_page,
                page_size=configuration_page_size,
                change_sort_key=change_sort_key,
                change_sort_direction=change_sort_direction,
                impact_sort_key=impact_sort_key,
                impact_sort_direction=impact_sort_direction,
                change_search=change_search,
                change_status=change_status,
                change_approval_status=change_approval_status,
                change_applied_state=change_applied_state,
                impact_search=impact_search,
                impact_type=impact_type,
                impact_applied_state=impact_applied_state,
            )
        )
        return FinancialsWorkspaceViewModel(
            overview=state.overview,
            selected_project_id=project_id,
            selected_change_id=changes["selected_change_id"],
            can_create_change=changes["can_create_change"],
            selected_change=changes["selected_change"],
            financial_changes=changes["financial_changes"],
            financial_change_impacts=changes["financial_change_impacts"],
            change_sort_key=changes["change_sort_key"],
            change_sort_direction=changes["change_sort_direction"],
            impact_sort_key=changes["impact_sort_key"],
            impact_sort_direction=changes["impact_sort_direction"],
            change_search=changes["change_search"],
            change_status=changes["change_status"],
            change_approval_status=changes["change_approval_status"],
            change_applied_state=changes["change_applied_state"],
            impact_search=changes["impact_search"],
            impact_type=changes["impact_type"],
            impact_applied_state=changes["impact_applied_state"],
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


def _months_before(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 - max(0, int(months))
    year, month_index = divmod(index, 12)
    month = month_index + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


__all__ = [
    "FINANCE_DESTINATIONS",
    "FINANCE_SUBSECTIONS",
    "build_destination_state",
    "build_shell_state",
    "normalize_destination",
    "normalize_subsection",
]
