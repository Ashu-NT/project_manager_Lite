from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
    format_hours,
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    BudgetLineFact,
    BudgetVersionFact,
    FinanceBudgetWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.configuration.models.setup_facts import (
    FinanceSetupCostCodeFact,
    FinanceSetupRestrictionFact,
    FinanceSetupWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.planned_costs.models.planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
    PlannedCostLineFact,
    PlannedCostVersionFact,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


class FinanceConfigurationViews(TypedDict):
    profile: FinancialsDetailViewModel
    can_create_cost_code: bool
    can_manage_restrictions: bool
    cost_codes: FinancialsCollectionViewModel
    restrictions: FinancialsCollectionViewModel
    cost_code_sort_key: str
    cost_code_sort_direction: str
    restriction_sort_key: str
    restriction_sort_direction: str
    budget_versions: FinancialsCollectionViewModel
    budget_lines: FinancialsCollectionViewModel
    rate_cards: FinancialsCollectionViewModel
    rate_lines: FinancialsCollectionViewModel
    planned_cost_versions: FinancialsCollectionViewModel
    planned_cost_lines: FinancialsCollectionViewModel
    selected_budget_id: str
    show_create_budget_version: bool
    can_create_budget_version: bool
    create_budget_version_disabled_reason: str
    budget_version_sort_key: str
    budget_version_sort_direction: str
    budget_line_sort_key: str
    budget_line_sort_direction: str
    selected_planned_cost_version_id: str
    planned_cost_version_sort_key: str
    planned_cost_version_sort_direction: str
    planned_cost_line_sort_key: str
    planned_cost_line_sort_direction: str


def _label(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Not set"


def _datetime_label(value: datetime | None) -> str:
    if value is None:
        return "Not set"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _profile(source: FinanceSetupWorkspaceFacts) -> FinancialsDetailViewModel:
    profile = source.profile
    return FinancialsDetailViewModel(
        id=profile.project_id,
        title="Financial Profile",
        empty_state=(
            "Select a project to review its financial profile."
            if not profile.project_id
            else "The project financial profile is not configured."
        ),
        status_label=_label(profile.status),
        subtitle="Canonical project finance configuration and control policy.",
        fields=(
            FinancialsDetailFieldViewModel("Currency", profile.currency_code),
            FinancialsDetailFieldViewModel(
                "Billing method", _label(profile.billing_method)
            ),
            FinancialsDetailFieldViewModel(
                "Budget control", _label(profile.budget_control_mode)
            ),
            FinancialsDetailFieldViewModel(
                "Cost-code policy", _label(profile.cost_code_policy)
            ),
            FinancialsDetailFieldViewModel(
                "Financial period",
                f"{_date_label(profile.financial_start_date)} to {_date_label(profile.financial_end_date)}",
            ),
            FinancialsDetailFieldViewModel(
                "Funding", "Funded" if profile.is_funded else "Not funded"
            ),
            FinancialsDetailFieldViewModel(
                "Billing", "Billable" if profile.is_billable else "Non-billable"
            ),
            FinancialsDetailFieldViewModel(
                "Default cost code", profile.default_cost_code or "Not set"
            ),
            FinancialsDetailFieldViewModel("Version", str(profile.version)),
        ),
        state={
            "version": profile.version,
            "status": profile.status,
            "currency": profile.currency_code,
            "billingMethod": profile.billing_method,
            "budgetControlMode": profile.budget_control_mode,
            "costCodePolicy": profile.cost_code_policy,
            "financialStartDate": profile.financial_start_date.isoformat()
            if profile.financial_start_date
            else "",
            "financialEndDate": profile.financial_end_date.isoformat()
            if profile.financial_end_date
            else "",
            "isFunded": profile.is_funded,
            "isBillable": profile.is_billable,
            "defaultCostCodeId": profile.default_cost_code_id or "",
            "defaultCostCodeLabel": profile.default_cost_code,
            "canEdit": source.can_edit_profile,
            "canTransition": source.can_transition_profile,
        },
    )


def _setup_cost_code_view(item: FinanceSetupCostCodeFact) -> FinancialsRecordViewModel:
    effective = (
        f"{_date_label(item.effective_from)} to {_date_label(item.effective_to)}"
    )
    external = (
        f"{item.external_system}: {item.external_reference}"
        if item.external_system and item.external_reference
        else "No external mapping"
    )
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.code,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=item.name,
        supporting_text=item.parent_code or "Root code",
        meta_text=effective,
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "code": item.code,
            "name": item.name,
            "description": item.description,
            "parentId": item.parent_id or "",
            "parentCode": item.parent_code,
            "externalSystem": item.external_system or "",
            "externalReference": item.external_reference or "",
            "effectiveFrom": item.effective_from.isoformat()
            if item.effective_from
            else "",
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


def _setup_restriction_view(
    item: FinanceSetupRestrictionFact,
) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.code,
        status_label="Active" if item.is_active else "Inactive",
        subtitle=item.name,
        supporting_text="Project default" if item.is_default else "Allowed for project",
        meta_text=_datetime_label(item.created_at),
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "costCodeId": item.cost_code_id,
            "isActive": item.is_active,
            "isDefault": item.is_default,
            "canRemove": item.can_remove,
        },
    )


def _budget_version_view(item: BudgetVersionFact) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
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
        can_primary_action=False,
        can_secondary_action=False,
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


def _budget_line_view(item: BudgetLineFact) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
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
        can_primary_action=False,
        can_secondary_action=False,
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


def _planned_cost_version_view(
    item: PlannedCostVersionFact,
) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=item.id,
        title=f"Planned cost v{item.revision}",
        status_label=_label(item.status),
        subtitle=f"As of {item.as_of.isoformat()} | {item.line_count} lines",
        supporting_text=(
            f"{format_money(item.total_amount, item.currency_code)} | "
            f"{format_hours(item.total_hours)}"
        ),
        meta_text=f"Calculated {_datetime_label(item.calculated_at)} by {item.calculated_by}",
        can_primary_action=False,
        can_secondary_action=False,
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


def _planned_cost_line_view(item: PlannedCostLineFact) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
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
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "versionId": item.version_id,
            "versionRevision": item.version_revision,
            "resourceCode": item.resource_code,
            "costCode": item.cost_code,
            "costCodeName": item.cost_code_name,
            "rateCardId": item.rate_card_id,
        },
    )


def build_finance_configuration_views(
    source: FinanceSetupWorkspaceFacts
    | FinanceBudgetWorkspaceFacts
    | FinancePlannedCostWorkspaceFacts
    | None,
) -> FinanceConfigurationViews:
    setup = source if isinstance(source, FinanceSetupWorkspaceFacts) else None
    budget = source if isinstance(source, FinanceBudgetWorkspaceFacts) else None
    planned = source if isinstance(source, FinancePlannedCostWorkspaceFacts) else None
    return {
        "profile": _profile(setup)
        if setup
        else FinancialsDetailViewModel(
            title="Financial Profile",
            status_label="Not configured",
            subtitle="Project-level currency, controls, and billing policy.",
            empty_state="Select a project to review its financial profile.",
        ),
        "can_create_cost_code": (setup.can_create_cost_code if setup else False),
        "can_manage_restrictions": (setup.can_manage_restrictions if setup else False),
        "cost_codes": FinancialsCollectionViewModel(
            title="Cost Codes",
            subtitle="Organization-owned financial classification codes.",
            empty_state="No cost codes match the current filters.",
            items=tuple(_setup_cost_code_view(item) for item in setup.cost_codes.items)
            if setup
            else (),
            page=(setup.cost_codes.page if setup else 1),
            page_size=(setup.cost_codes.page_size if setup else 50),
            total=(setup.cost_codes.total if setup else 0),
        ),
        "restrictions": FinancialsCollectionViewModel(
            title="Project Allow-list",
            subtitle="Cost codes explicitly available under the Restricted policy.",
            empty_state="No cost-code restrictions are configured for this project.",
            items=tuple(
                _setup_restriction_view(item) for item in setup.restrictions.items
            )
            if setup
            else (),
            page=(setup.restrictions.page if setup else 1),
            page_size=(setup.restrictions.page_size if setup else 50),
            total=(setup.restrictions.total if setup else 0),
        ),
        "cost_code_sort_key": (setup.cost_codes.sort_key if setup else "code"),
        "cost_code_sort_direction": (
            setup.cost_codes.sort_direction if setup else "asc"
        ),
        "restriction_sort_key": (setup.restrictions.sort_key if setup else "code"),
        "restriction_sort_direction": (
            setup.restrictions.sort_direction if setup else "asc"
        ),
        "budget_versions": FinancialsCollectionViewModel(
            title="Budget Versions",
            subtitle="Governed budget revisions and approval state.",
            empty_state="No budget version exists for this project.",
            items=tuple(_budget_version_view(item) for item in budget.versions.items)
            if budget
            else (),
            page=(budget.versions.page if budget else 1),
            page_size=(budget.versions.page_size if budget else 50),
            total=(budget.versions.total if budget else 0),
        ),
        "budget_lines": FinancialsCollectionViewModel(
            title="Budget Lines",
            subtitle="Authorized amounts by cost code and WBS task.",
            empty_state="No budget lines exist for this project.",
            items=tuple(_budget_line_view(item) for item in budget.lines.items)
            if budget
            else (),
            page=(budget.lines.page if budget else 1),
            page_size=(budget.lines.page_size if budget else 50),
            total=(budget.lines.total if budget else 0),
        ),
        "rate_cards": FinancialsCollectionViewModel(
            title="Rate Cards",
            subtitle="Project and organization rate sources visible to this project.",
            empty_state="No rate cards are visible to this project.",
            items=(),
        ),
        "rate_lines": FinancialsCollectionViewModel(
            title="Rate Lines",
            subtitle="Effective cost and billing rate definitions.",
            empty_state="No rate lines exist on the visible cards.",
            items=(),
            page=1,
            page_size=50,
            total=0,
        ),
        "planned_cost_versions": FinancialsCollectionViewModel(
            title="Planned Cost Snapshots",
            subtitle="Versioned assignment-based labor calculations.",
            empty_state="No planned-cost snapshot has been calculated.",
            items=tuple(
                _planned_cost_version_view(item) for item in planned.versions.items
            )
            if planned
            else (),
            page=(planned.versions.page if planned else 1),
            page_size=(planned.versions.page_size if planned else 50),
            total=(planned.versions.total if planned else 0),
        ),
        "planned_cost_lines": FinancialsCollectionViewModel(
            title="Planned Cost Lines",
            subtitle="Calculated labor cost by task, resource, and cost code.",
            empty_state="No planned-cost lines exist for this project.",
            items=tuple(_planned_cost_line_view(item) for item in planned.lines.items)
            if planned
            else (),
            page=(planned.lines.page if planned else 1),
            page_size=(planned.lines.page_size if planned else 50),
            total=(planned.lines.total if planned else 0),
        ),
        "selected_budget_id": (budget.selected_budget_id if budget else ""),
        "show_create_budget_version": (budget.show_create_version if budget else False),
        "can_create_budget_version": (budget.can_create_version if budget else False),
        "create_budget_version_disabled_reason": (
            budget.create_version_disabled_reason if budget else ""
        ),
        "budget_version_sort_key": (budget.versions.sort_key if budget else "revision"),
        "budget_version_sort_direction": (
            budget.versions.sort_direction if budget else "desc"
        ),
        "budget_line_sort_key": (budget.lines.sort_key if budget else "metaText"),
        "budget_line_sort_direction": (
            budget.lines.sort_direction if budget else "desc"
        ),
        "selected_planned_cost_version_id": (
            planned.selected_version_id if planned else ""
        ),
        "planned_cost_version_sort_key": (
            planned.versions.sort_key if planned else "revision"
        ),
        "planned_cost_version_sort_direction": (
            planned.versions.sort_direction if planned else "desc"
        ),
        "planned_cost_line_sort_key": (planned.lines.sort_key if planned else "title"),
        "planned_cost_line_sort_direction": (
            planned.lines.sort_direction if planned else "asc"
        ),
    }


__all__ = ["build_finance_configuration_views"]
