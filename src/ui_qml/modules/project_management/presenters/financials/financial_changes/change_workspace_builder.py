from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.financial_changes.models.change_facts import (
    FinanceChangeWorkspaceFacts,
    FinancialChangeDetailFact,
    FinancialChangeImpactFact,
    FinancialChangeSummaryFact,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


class FinanceChangeViews(TypedDict):
    selected_change_id: str
    selected_change: FinancialsDetailViewModel
    financial_changes: FinancialsCollectionViewModel
    financial_change_impacts: FinancialsCollectionViewModel
    change_sort_key: str
    change_sort_direction: str
    impact_sort_key: str
    impact_sort_direction: str
    change_search: str
    change_status: str
    change_approval_status: str
    change_applied_state: str
    impact_search: str
    impact_type: str
    impact_applied_state: str
    can_create_change: bool


def build_change_workspace_views(
    source: FinanceChangeWorkspaceFacts,
    *,
    change_search: str = "",
    change_status: str = "",
    change_approval_status: str = "",
    change_applied_state: str = "",
    impact_search: str = "",
    impact_type: str = "",
    impact_applied_state: str = "",
) -> FinanceChangeViews:
    selected = source.selected_change
    return {
        "selected_change_id": source.selected_change_id,
        "selected_change": _detail(selected)
        if selected is not None
        else FinancialsDetailViewModel(
            empty_state="Select a Change Request to inspect its governance and impacts.",
        ),
        "financial_changes": FinancialsCollectionViewModel(
            title="Change Requests",
            subtitle="Governed requests with snapshotted Finance bases.",
            empty_state="No Change Requests match the current filters.",
            items=tuple(_change_record(item) for item in source.changes.items),
            page=source.changes.page,
            page_size=source.changes.page_size,
            total=source.changes.total,
        ),
        "financial_change_impacts": FinancialsCollectionViewModel(
            title="Selected Change Impacts",
            subtitle="Typed Budget, Forecast, and Schedule evidence.",
            empty_state=(
                "Select a Change Request."
                if not source.selected_change_id
                else "No impacts match the current filters."
            ),
            items=tuple(_impact_record(item) for item in source.impacts.items),
            page=source.impacts.page,
            page_size=source.impacts.page_size,
            total=source.impacts.total,
        ),
        "change_sort_key": source.changes.sort_key,
        "change_sort_direction": source.changes.sort_direction,
        "impact_sort_key": source.impacts.sort_key,
        "impact_sort_direction": source.impacts.sort_direction,
        "change_search": change_search,
        "change_status": change_status,
        "change_approval_status": change_approval_status,
        "change_applied_state": change_applied_state,
        "impact_search": impact_search,
        "impact_type": impact_type,
        "impact_applied_state": impact_applied_state,
        "can_create_change": source.can_create,
    }


def _change_record(item: FinancialChangeSummaryFact) -> FinancialsRecordViewModel:
    budget_base = _revision_label(item.base_budget_id, item.base_budget_revision)
    forecast_base = _revision_label(item.base_forecast_id, item.base_forecast_revision)
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.title,
        status_label=_label(item.status),
        subtitle=f"Revision {item.revision} | Effective {item.effective_date.isoformat()}",
        supporting_text=(
            f"{item.impact_count} impact{'s' if item.impact_count != 1 else ''} | "
            f"Approval: {_label(item.approval_status) or 'Not requested'}"
        ),
        meta_text=(
            f"Applied {_datetime_label(item.applied_at)}"
            if item.applied_at
            else f"Created {_datetime_label(item.created_at)}"
        ),
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "revision": item.revision,
            "version": item.row_version,
            "currency": item.currency_code,
            "reason": item.reason,
            "createdBy": item.created_by,
            "budgetBase": budget_base,
            "forecastBase": forecast_base,
            "approvalStatus": item.approval_status,
            "impactCount": item.impact_count,
        },
    )


def _detail(item: FinancialChangeDetailFact) -> FinancialsDetailViewModel:
    return FinancialsDetailViewModel(
        empty_state="Select a Change Request to inspect its governance and impacts.",
        id=item.id,
        title=item.title,
        status_label=_label(item.status),
        subtitle=f"Revision {item.revision} | Effective {item.effective_date.isoformat()}",
        description=item.description or item.reason,
        fields=tuple(
            FinancialsDetailFieldViewModel(*field)
            for field in (
                ("Reason", item.reason, "Governed request rationale"),
                (
                    "Currency",
                    item.currency_code,
                    "Monetary impacts retain their own currency",
                ),
                (
                    "Budget base",
                    _base_label(
                        item.base_budget_id,
                        item.base_budget_revision,
                        item.base_budget_is_current,
                    ),
                    _current_label(
                        item.current_budget_id, item.current_budget_revision
                    ),
                ),
                (
                    "Forecast base",
                    _base_label(
                        item.base_forecast_id,
                        item.base_forecast_revision,
                        item.base_forecast_is_current,
                    ),
                    _current_label(
                        item.current_forecast_id, item.current_forecast_revision
                    ),
                ),
                (
                    "Approval",
                    _label(item.approval_status) or "Not requested",
                    item.approval_request_id or "",
                ),
                (
                    "Requested by",
                    item.approval_requested_by or item.submitted_by or "-",
                    _datetime_label(item.approval_requested_at or item.submitted_at),
                ),
                (
                    "Decision",
                    item.approval_decided_by or item.rejected_by or "Not decided",
                    _decision_support(item),
                ),
                (
                    "Applied Budget",
                    _revision_label(
                        item.applied_budget_id, item.applied_budget_revision
                    ),
                    "Stored successor reference",
                ),
                (
                    "Applied Forecast",
                    _revision_label(
                        item.applied_forecast_id, item.applied_forecast_revision
                    ),
                    "Stored successor reference",
                ),
                (
                    "Schedule applications",
                    str(item.applied_schedule_count),
                    "Scheduling remains authoritative",
                ),
                (
                    "Impacts",
                    str(item.impact_count),
                    "Independent of the visible impact page",
                ),
                (
                    "Row version",
                    str(item.row_version),
                    f"Request revision {item.revision}",
                ),
            )
        ),
        state={
            "baseBudgetIsCurrent": item.base_budget_is_current,
            "baseForecastIsCurrent": item.base_forecast_is_current,
            "approvalRequestId": item.approval_request_id or "",
            "appliedBudgetId": item.applied_budget_id or "",
            "appliedForecastId": item.applied_forecast_id or "",
            "appliedScheduleCount": item.applied_schedule_count,
            "version": item.row_version,
            "reason": item.reason,
            "description": item.description,
            "effectiveDate": item.effective_date.isoformat(),
            "currency": item.currency_code,
            "canEdit": item.can_edit,
            "canAddImpact": item.can_add_impact,
            "canSubmit": item.can_submit,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
        },
    )


def _impact_record(item: FinancialChangeImpactFact) -> FinancialsRecordViewModel:
    monetary = item.impact_type in {"budget", "forecast"}
    subtitle = (
        format_money(item.amount, item.currency_code or "")
        if monetary
        else _schedule_range(item.schedule_start, item.schedule_finish)
    )
    target = _impact_target(item)
    applied = (
        f"{_label(item.applied_reference_type)}: {item.applied_reference_id}"
        if item.applied_reference_id
        else "Not applied"
    )
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.description,
        status_label=_label(item.impact_type),
        subtitle=subtitle,
        supporting_text=target,
        meta_text=applied,
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "changeRequestId": item.change_request_id,
            "impactType": item.impact_type,
            "amount": str(item.amount),
            "currency": item.currency_code or "",
            "costCodeId": item.cost_code_id or "",
            "costCode": item.cost_code,
            "taskId": item.task_id or "",
            "targetLineId": item.target_line_id or "",
            "targetTaskVersion": item.target_task_version or 0,
            "scheduleStart": _date_value(item.schedule_start),
            "scheduleFinish": _date_value(item.schedule_finish),
            "appliedReferenceType": item.applied_reference_type or "",
            "appliedReferenceId": item.applied_reference_id or "",
            "version": item.row_version,
            "canEdit": item.can_edit,
            "canRemove": item.can_remove,
        },
    )


def _impact_target(item: FinancialChangeImpactFact) -> str:
    if item.impact_type == "schedule":
        return (
            " | ".join(
                part
                for part in (
                    f"{item.wbs_code} {item.task_name}".strip(),
                    f"Task version {item.target_task_version}"
                    if item.target_task_version
                    else "",
                )
                if part
            )
            or "Task reference unavailable"
        )
    return (
        " | ".join(
            part
            for part in (
                f"{item.cost_code} {item.cost_code_name}".strip(),
                f"Target line {item.target_line_id}" if item.target_line_id else "",
            )
            if part
        )
        or "New financial line"
    )


def _base_label(
    identifier: str | None, revision: int | None, current: bool | None
) -> str:
    if not identifier:
        return "Not captured"
    state = "Current" if current else "Stale"
    return f"Revision {revision} | {state}"


def _current_label(identifier: str | None, revision: int | None) -> str:
    return (
        f"Current approved: revision {revision}"
        if identifier
        else "No current approved version"
    )


def _revision_label(identifier: str | None, revision: int | None) -> str:
    if not identifier:
        return "Not available"
    return f"Revision {revision}" if revision is not None else identifier


def _decision_support(item: FinancialChangeDetailFact) -> str:
    timestamp = item.approval_decided_at or item.rejected_at or item.applied_at
    parts = (
        _datetime_label(timestamp),
        item.approval_decision_note or item.rejection_notes,
    )
    return " | ".join(part for part in parts if part)


def _schedule_range(start: date | None, finish: date | None) -> str:
    return (
        f"{_date_value(start) or 'Unchanged'} to {_date_value(finish) or 'Unchanged'}"
    )


def _date_value(value: date | None) -> str:
    return value.isoformat() if value else ""


def _datetime_label(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else ""


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


__all__ = ["build_change_workspace_views"]
