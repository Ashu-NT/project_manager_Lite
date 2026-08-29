from __future__ import annotations

from datetime import date, datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
    format_hours,
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationFieldDto,
    FinancialConfigurationRecordDto,
    FinancialConfigurationWorkspaceDto,
    FinancialProfileDto,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinanceBudgetWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
)


def _label(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Not set"


def _datetime_label(value: datetime | None) -> str:
    if value is None:
        return "Not set"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def serialize_finance_setup_workspace(
    source: FinanceSetupFacts,
) -> FinancialConfigurationWorkspaceDto:
    return FinancialConfigurationWorkspaceDto(
        profile=FinancialProfileDto(
            project_id=source.project_id,
            status_label=_label(source.status),
            subtitle="Canonical project finance configuration and control policy.",
            fields=(
                FinancialConfigurationFieldDto("Currency", source.currency_code),
                FinancialConfigurationFieldDto("Billing method", _label(source.billing_method)),
                FinancialConfigurationFieldDto("Budget control", _label(source.budget_control_mode)),
                FinancialConfigurationFieldDto("Cost-code policy", _label(source.cost_code_policy)),
                FinancialConfigurationFieldDto(
                    "Financial period",
                    f"{_date_label(source.financial_start_date)} to {_date_label(source.financial_end_date)}",
                ),
                FinancialConfigurationFieldDto("Funding", "Funded" if source.is_funded else "Not funded"),
                FinancialConfigurationFieldDto("Billing", "Billable" if source.is_billable else "Non-billable"),
                FinancialConfigurationFieldDto("Default cost code", source.default_cost_code or "Not set"),
                FinancialConfigurationFieldDto("Version", str(source.version)),
            ),
        )
    )


def serialize_finance_budget_workspace(
    source: FinanceBudgetWorkspaceFacts,
) -> FinancialConfigurationWorkspaceDto:
    return FinancialConfigurationWorkspaceDto(
        selected_budget_id=source.selected_budget_id,
        budget_versions=tuple(_budget_version_dto(item) for item in source.versions.items),
        budget_version_page=source.versions.page,
        budget_version_page_size=source.versions.page_size,
        budget_version_total=source.versions.total,
        budget_version_sort_key=source.versions.sort_key,
        budget_version_sort_direction=source.versions.sort_direction,
        budget_lines=tuple(_budget_line_dto(item) for item in source.lines.items),
        budget_line_page=source.lines.page,
        budget_line_page_size=source.lines.page_size,
        budget_line_total=source.lines.total,
        budget_line_sort_key=source.lines.sort_key,
        budget_line_sort_direction=source.lines.sort_direction,
    )


def serialize_finance_planned_cost_workspace(
    source: FinancePlannedCostWorkspaceFacts,
) -> FinancialConfigurationWorkspaceDto:
    return FinancialConfigurationWorkspaceDto(
        selected_planned_cost_version_id=source.selected_version_id,
        planned_cost_versions=tuple(
            _planned_cost_version_dto(item) for item in source.versions.items
        ),
        planned_cost_version_page=source.versions.page,
        planned_cost_version_page_size=source.versions.page_size,
        planned_cost_version_total=source.versions.total,
        planned_cost_version_sort_key=source.versions.sort_key,
        planned_cost_version_sort_direction=source.versions.sort_direction,
        planned_cost_lines=tuple(
            _planned_cost_line_dto(item) for item in source.lines.items
        ),
        planned_cost_line_page=source.lines.page,
        planned_cost_line_page_size=source.lines.page_size,
        planned_cost_line_total=source.lines.total,
        planned_cost_line_sort_key=source.lines.sort_key,
        planned_cost_line_sort_direction=source.lines.sort_direction,
    )


def _budget_version_dto(item) -> FinancialConfigurationRecordDto:
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=f"v{item.revision} - {item.name}",
        status_label=_label(item.status),
        subtitle=f"{item.line_count} line{'s' if item.line_count != 1 else ''}",
        supporting_text=f"Authorized total {format_money(item.total_amount, item.currency_code)}",
        meta_text=(
            f"Approved {_datetime_label(item.approved_at)} by "
            f"{item.approved_by or 'not approved'}"
            if item.status == "approved"
            else f"Updated row version {item.row_version}"
        ),
        state={
            "revision": item.revision,
            "currency": item.currency_code,
            "totalAmountLabel": format_money(item.total_amount, item.currency_code),
            "lineCount": item.line_count,
            "notes": item.notes,
        },
    )


def _budget_line_dto(item) -> FinancialConfigurationRecordDto:
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=item.description or f"{item.cost_code} budget line",
        status_label=_label(item.budget_status),
        subtitle=(
            f"{item.cost_code} - {item.cost_code_name}"
            if item.cost_code_name
            else item.cost_code
        ),
        supporting_text=f"{item.task_name} | {format_money(item.amount, item.currency_code)}",
        meta_text=f"Budget v{item.budget_revision} - {item.budget_name}",
        state={
            "budgetId": item.budget_id,
            "budgetRevision": item.budget_revision,
            "costCode": item.cost_code,
            "taskName": item.task_name,
            "wbsCode": item.wbs_code,
            "amountLabel": format_money(item.amount, item.currency_code),
        },
    )


def _planned_cost_version_dto(item) -> FinancialConfigurationRecordDto:
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=f"Planned cost v{item.revision}",
        status_label=_label(item.status),
        subtitle=f"As of {item.as_of.isoformat()} | {item.line_count} lines",
        supporting_text=(
            f"{format_money(item.total_amount, item.currency_code)} | "
            f"{format_hours(item.total_hours)}"
        ),
        meta_text=f"Calculated {_datetime_label(item.calculated_at)} by {item.calculated_by}",
        state={
            "revision": item.revision,
            "ratesComplete": item.rates_complete,
            "allocationsComplete": item.allocations_complete,
            "costCodesComplete": item.cost_codes_complete,
            "unresolvedRateCount": item.unresolved_rate_count,
            "partiallyAllocatedResourceCount": item.partially_allocated_resource_count,
            "unclassifiedLineCount": item.unclassified_line_count,
            "totalAmountLabel": format_money(item.total_amount, item.currency_code),
            "totalHoursLabel": format_hours(item.total_hours),
        },
    )


def _planned_cost_line_dto(item) -> FinancialConfigurationRecordDto:
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=item.task_name,
        status_label=_label(item.version_status),
        subtitle=(
            f"{item.wbs_code} | {item.resource_name}"
            if item.wbs_code
            else item.resource_name
        ),
        supporting_text=(
            f"{format_hours(item.planned_hours)} x "
            f"{format_money(item.rate_amount, item.currency_code)} = "
            f"{format_money(item.amount, item.currency_code)}"
        ),
        meta_text=(
            f"Snapshot v{item.version_revision} | {item.cost_code} | "
            f"Rate-card v{item.rate_card_version}"
        ),
        state={
            "versionId": item.version_id,
            "versionRevision": item.version_revision,
            "resourceCode": getattr(item, "resource_code", ""),
            "costCode": item.cost_code,
            "costCodeName": item.cost_code_name,
            "rateCardId": item.rate_card_id,
        },
    )


__all__ = [
    "serialize_finance_budget_workspace",
    "serialize_finance_setup_workspace",
    "serialize_finance_planned_cost_workspace",
]
