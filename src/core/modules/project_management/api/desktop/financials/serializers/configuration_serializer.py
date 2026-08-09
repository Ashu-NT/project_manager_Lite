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
from src.core.modules.project_management.application.financials import (
    ProjectFinanceWorkspaceRead,
)


def _label(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Not set"


def _datetime_label(value: datetime | None) -> str:
    if value is None:
        return "Not set"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def serialize_finance_configuration_workspace(
    source: ProjectFinanceWorkspaceRead,
) -> FinancialConfigurationWorkspaceDto:
    profile = source.profile
    profile_dto = FinancialProfileDto(
        project_id=source.project_id,
        status_label=_label(profile.status.value),
        subtitle="Canonical project finance configuration and control policy.",
        fields=(
            FinancialConfigurationFieldDto("Currency", profile.currency_code),
            FinancialConfigurationFieldDto(
                "Billing method", _label(profile.billing_method.value)
            ),
            FinancialConfigurationFieldDto(
                "Budget control", _label(profile.budget_control_mode.value)
            ),
            FinancialConfigurationFieldDto(
                "Cost-code policy", _label(profile.cost_code_policy.value)
            ),
            FinancialConfigurationFieldDto(
                "Financial period",
                f"{_date_label(profile.financial_start_date)} to "
                f"{_date_label(profile.financial_end_date)}",
            ),
            FinancialConfigurationFieldDto(
                "Funding", "Funded" if profile.is_funded else "Not funded"
            ),
            FinancialConfigurationFieldDto(
                "Billing", "Billable" if profile.is_billable else "Non-billable"
            ),
            FinancialConfigurationFieldDto(
                "Default cost code", source.default_cost_code or "Not set"
            ),
            FinancialConfigurationFieldDto("Version", str(profile.version)),
        ),
    )

    return FinancialConfigurationWorkspaceDto(
        profile=profile_dto,
        budget_versions=tuple(
            FinancialConfigurationRecordDto(
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
            for item in source.budget_versions
        ),
        budget_lines=tuple(
            FinancialConfigurationRecordDto(
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
            for item in source.budget_lines
        ),
        budget_line_page=source.budget_line_page,
        budget_line_page_size=source.budget_line_page_size,
        budget_line_total=source.budget_line_total,
        rate_cards=tuple(
            FinancialConfigurationRecordDto(
                id=item.id,
                title=item.name,
                status_label="Active" if item.is_active else "Inactive",
                subtitle=f"{_label(item.scope)} scope",
                supporting_text=f"{item.line_count} rate line{'s' if item.line_count != 1 else ''}",
                meta_text=("Legacy-seeded" if item.is_legacy else f"Version {item.version}"),
                state={
                    "scope": item.scope,
                    "isLegacy": item.is_legacy,
                    "lineCount": item.line_count,
                },
            )
            for item in source.rate_cards
        ),
        rate_lines=tuple(
            FinancialConfigurationRecordDto(
                id=item.id,
                title=f"{_label(item.rate_type)} rate - {item.rate_card_name}",
                status_label="Active" if item.is_active else "Inactive",
                subtitle=(
                    item.resource_name
                    or item.role
                    or item.skill_code
                    or "Default rate"
                ),
                supporting_text=(
                    f"{format_money(item.rate_amount, item.rate_currency)} / "
                    f"{item.unit.lower()}"
                ),
                meta_text=(
                    f"{_label(item.card_scope)} | {_label(item.origin)} | "
                    f"{_date_label(item.effective_from)} to {_date_label(item.effective_to)}"
                ),
                state={
                    "rateCardId": item.rate_card_id,
                    "rateType": item.rate_type,
                    "origin": item.origin,
                    "departmentId": item.department_id,
                },
            )
            for item in source.rate_lines
        ),
        rate_line_page=source.rate_line_page,
        rate_line_page_size=source.rate_line_page_size,
        rate_line_total=source.rate_line_total,
        planned_cost_versions=tuple(
            FinancialConfigurationRecordDto(
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
            for item in source.planned_cost_versions
        ),
        planned_cost_lines=tuple(
            FinancialConfigurationRecordDto(
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
                    "costCode": item.cost_code,
                    "costCodeName": item.cost_code_name,
                    "rateCardId": item.rate_card_id,
                },
            )
            for item in source.planned_cost_lines
        ),
        planned_cost_line_page=source.planned_cost_line_page,
        planned_cost_line_page_size=source.planned_cost_line_page_size,
        planned_cost_line_total=source.planned_cost_line_total,
    )


__all__ = ["serialize_finance_configuration_workspace"]
