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
    FinanceSetupWorkspaceFacts,
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
    source: FinanceSetupWorkspaceFacts,
) -> FinancialConfigurationWorkspaceDto:
    profile = source.profile
    return FinancialConfigurationWorkspaceDto(
        profile=FinancialProfileDto(
            project_id=profile.project_id,
            status_label=_label(profile.status),
            subtitle="Canonical project finance configuration and control policy.",
            fields=(
                FinancialConfigurationFieldDto("Currency", profile.currency_code),
                FinancialConfigurationFieldDto("Billing method", _label(profile.billing_method)),
                FinancialConfigurationFieldDto("Budget control", _label(profile.budget_control_mode)),
                FinancialConfigurationFieldDto("Cost-code policy", _label(profile.cost_code_policy)),
                FinancialConfigurationFieldDto(
                    "Financial period",
                    f"{_date_label(profile.financial_start_date)} to {_date_label(profile.financial_end_date)}",
                ),
                FinancialConfigurationFieldDto("Funding", "Funded" if profile.is_funded else "Not funded"),
                FinancialConfigurationFieldDto("Billing", "Billable" if profile.is_billable else "Non-billable"),
                FinancialConfigurationFieldDto("Default cost code", profile.default_cost_code or "Not set"),
                FinancialConfigurationFieldDto("Version", str(profile.version)),
            ),
            state={
                "version": profile.version,
                "status": profile.status,
                "currency": profile.currency_code,
                "billingMethod": profile.billing_method,
                "budgetControlMode": profile.budget_control_mode,
                "costCodePolicy": profile.cost_code_policy,
                "financialStartDate": profile.financial_start_date.isoformat() if profile.financial_start_date else "",
                "financialEndDate": profile.financial_end_date.isoformat() if profile.financial_end_date else "",
                "isFunded": profile.is_funded,
                "isBillable": profile.is_billable,
                "defaultCostCodeId": profile.default_cost_code_id or "",
                "defaultCostCodeLabel": profile.default_cost_code,
                "canEdit": source.can_edit_profile,
                "canTransition": source.can_transition_profile,
            },
        ),
        can_create_cost_code=source.can_create_cost_code,
        can_manage_restrictions=source.can_manage_restrictions,
        cost_codes=tuple(_setup_cost_code_dto(item) for item in source.cost_codes.items),
        cost_code_page=source.cost_codes.page,
        cost_code_page_size=source.cost_codes.page_size,
        cost_code_total=source.cost_codes.total,
        cost_code_sort_key=source.cost_codes.sort_key,
        cost_code_sort_direction=source.cost_codes.sort_direction,
        restrictions=tuple(_setup_restriction_dto(item) for item in source.restrictions.items),
        restriction_page=source.restrictions.page,
        restriction_page_size=source.restrictions.page_size,
        restriction_total=source.restrictions.total,
        restriction_sort_key=source.restrictions.sort_key,
        restriction_sort_direction=source.restrictions.sort_direction,
    )


def _setup_cost_code_dto(item) -> FinancialConfigurationRecordDto:
    effective = f"{_date_label(item.effective_from)} to {_date_label(item.effective_to)}"
    external = (
        f"{item.external_system}: {item.external_reference}"
        if item.external_system and item.external_reference
        else "No external mapping"
    )
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=item.code,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=item.name,
        supporting_text=item.parent_code or "Root code",
        meta_text=effective,
        state={
            "code": item.code,
            "name": item.name,
            "description": item.description,
            "parentId": item.parent_id or "",
            "parentCode": item.parent_code,
            "externalSystem": item.external_system or "",
            "externalReference": item.external_reference or "",
            "effectiveFrom": item.effective_from.isoformat() if item.effective_from else "",
            "effectiveTo": item.effective_to.isoformat() if item.effective_to else "",
            "isActive": item.is_active,
            "isAssigned": item.is_assigned,
            "isDefault": item.is_default,
            "version": item.version,
            "externalLabel": external,
            "canEdit": item.can_edit,
            "canChangeStatus": item.can_change_status,
            "canAddRestriction": item.can_add_restriction,
            "canRemoveRestriction": item.can_remove_restriction,
        },
    )


def _setup_restriction_dto(item) -> FinancialConfigurationRecordDto:
    return FinancialConfigurationRecordDto(
        id=item.id,
        title=item.code,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=item.name,
        supporting_text="Project default" if item.is_default else "Allowed for project",
        meta_text=_datetime_label(item.created_at),
        state={
            "costCodeId": item.cost_code_id,
            "isActive": item.is_active,
            "isDefault": item.is_default,
            "canRemove": item.can_remove,
        },
    )


def serialize_finance_budget_workspace(
    source: FinanceBudgetWorkspaceFacts,
) -> FinancialConfigurationWorkspaceDto:
    return FinancialConfigurationWorkspaceDto(
        selected_budget_id=source.selected_budget_id,
        show_create_budget_version=source.show_create_version,
        can_create_budget_version=source.can_create_version,
        create_budget_version_disabled_reason=source.create_version_disabled_reason,
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
            "status": item.status,
            "rowVersion": item.row_version,
            "revision": item.revision,
            "predecessorBudgetId": item.predecessor_budget_id or "",
            "currency": item.currency_code,
            "totalAmountLabel": format_money(item.total_amount, item.currency_code),
            "lineCount": item.line_count,
            "notes": item.notes,
            "approvalRequestId": item.approval_request_id or "",
            "canEdit": item.can_edit,
            "canDelete": item.can_delete,
            "canAddLine": item.can_add_line,
            "canSubmit": item.can_submit,
            "canRequestApproval": item.can_request_approval,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
            "canCreateSuccessor": item.can_create_successor,
            "canClose": item.can_close,
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
            "rowVersion": item.row_version,
            "budgetRevision": item.budget_revision,
            "costCodeId": item.cost_code_id,
            "costCode": item.cost_code,
            "taskId": item.task_id or "",
            "taskName": item.task_name,
            "wbsCode": item.wbs_code,
            "amount": format_decimal_amount(item.amount, grouping=False),
            "currency": item.currency_code,
            "amountLabel": format_money(item.amount, item.currency_code),
            "canEdit": item.can_edit,
            "canDelete": item.can_delete,
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
