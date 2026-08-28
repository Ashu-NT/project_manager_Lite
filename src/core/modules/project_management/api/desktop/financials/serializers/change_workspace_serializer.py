from __future__ import annotations

from datetime import date, datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.changes import (
    FinancialChangeDetailDto,
    FinancialChangeTableRecordDto,
    FinancialChangeWorkspaceDto,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinanceChangeWorkspaceFacts,
)


def serialize_finance_change_workspace(
    source: FinanceChangeWorkspaceFacts,
    *,
    change_search: str = "",
    change_status: str = "",
    change_approval_status: str = "",
    change_applied_state: str = "",
    impact_search: str = "",
    impact_type: str = "",
    impact_applied_state: str = "",
) -> FinancialChangeWorkspaceDto:
    selected = source.selected_change
    detail = _detail(selected) if selected is not None else FinancialChangeDetailDto()
    return FinancialChangeWorkspaceDto(
        selected_change_id=source.selected_change_id,
        selected_change=detail,
        changes=tuple(_change_record(item) for item in source.changes.items),
        change_page=source.changes.page,
        change_page_size=source.changes.page_size,
        change_total=source.changes.total,
        change_sort_key=source.changes.sort_key,
        change_sort_direction=source.changes.sort_direction,
        impacts=tuple(_impact_record(item) for item in source.impacts.items),
        impact_page=source.impacts.page,
        impact_page_size=source.impacts.page_size,
        impact_total=source.impacts.total,
        impact_sort_key=source.impacts.sort_key,
        impact_sort_direction=source.impacts.sort_direction,
        change_search=change_search,
        change_status=change_status,
        change_approval_status=change_approval_status,
        change_applied_state=change_applied_state,
        impact_search=impact_search,
        impact_type=impact_type,
        impact_applied_state=impact_applied_state,
    )


def _change_record(item) -> FinancialChangeTableRecordDto:
    budget_base = _revision_label(item.base_budget_id, item.base_budget_revision)
    forecast_base = _revision_label(item.base_forecast_id, item.base_forecast_revision)
    return FinancialChangeTableRecordDto(
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


def _detail(item) -> FinancialChangeDetailDto:
    return FinancialChangeDetailDto(
        id=item.id,
        title=item.title,
        status_label=_label(item.status),
        subtitle=f"Revision {item.revision} | Effective {item.effective_date.isoformat()}",
        description=item.description or item.reason,
        fields=(
            ("Reason", item.reason, "Governed request rationale"),
            ("Currency", item.currency_code, "Monetary impacts retain their own currency"),
            ("Budget base", _base_label(
                item.base_budget_id,
                item.base_budget_revision,
                item.base_budget_is_current,
            ), _current_label(item.current_budget_id, item.current_budget_revision)),
            ("Forecast base", _base_label(
                item.base_forecast_id,
                item.base_forecast_revision,
                item.base_forecast_is_current,
            ), _current_label(item.current_forecast_id, item.current_forecast_revision)),
            ("Approval", _label(item.approval_status) or "Not requested", item.approval_request_id or ""),
            ("Requested by", item.approval_requested_by or item.submitted_by or "-", _datetime_label(item.approval_requested_at or item.submitted_at)),
            ("Decision", item.approval_decided_by or item.rejected_by or "Not decided", _decision_support(item)),
            ("Applied Budget", _revision_label(item.applied_budget_id, item.applied_budget_revision), "Stored successor reference"),
            ("Applied Forecast", _revision_label(item.applied_forecast_id, item.applied_forecast_revision), "Stored successor reference"),
            ("Schedule applications", str(item.applied_schedule_count), "Scheduling remains authoritative"),
            ("Impacts", str(item.impact_count), "Independent of the visible impact page"),
            ("Row version", str(item.row_version), f"Request revision {item.revision}"),
        ),
        state={
            "baseBudgetIsCurrent": item.base_budget_is_current,
            "baseForecastIsCurrent": item.base_forecast_is_current,
            "approvalRequestId": item.approval_request_id or "",
            "appliedBudgetId": item.applied_budget_id or "",
            "appliedForecastId": item.applied_forecast_id or "",
            "appliedScheduleCount": item.applied_schedule_count,
            "version": item.row_version,
        },
    )


def _impact_record(item) -> FinancialChangeTableRecordDto:
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
    return FinancialChangeTableRecordDto(
        id=item.id,
        title=item.description,
        status_label=_label(item.impact_type),
        subtitle=subtitle,
        supporting_text=target,
        meta_text=applied,
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
        },
    )


def _impact_target(item) -> str:
    if item.impact_type == "schedule":
        return " | ".join(
            part
            for part in (
                f"{item.wbs_code} {item.task_name}".strip(),
                f"Task version {item.target_task_version}" if item.target_task_version else "",
            )
            if part
        ) or "Task reference unavailable"
    return " | ".join(
        part
        for part in (
            f"{item.cost_code} {item.cost_code_name}".strip(),
            f"Target line {item.target_line_id}" if item.target_line_id else "",
        )
        if part
    ) or "New financial line"


def _base_label(identifier: str | None, revision: int | None, current: bool | None) -> str:
    if not identifier:
        return "Not captured"
    state = "Current" if current else "Stale"
    return f"Revision {revision} | {state}"


def _current_label(identifier: str | None, revision: int | None) -> str:
    return f"Current approved: revision {revision}" if identifier else "No current approved version"


def _revision_label(identifier: str | None, revision: int | None) -> str:
    if not identifier:
        return "Not available"
    return f"Revision {revision}" if revision is not None else identifier


def _decision_support(item) -> str:
    timestamp = item.approval_decided_at or item.rejected_at or item.applied_at
    parts = (_datetime_label(timestamp), item.approval_decision_note or item.rejection_notes)
    return " | ".join(part for part in parts if part)


def _schedule_range(start: date | None, finish: date | None) -> str:
    return f"{_date_value(start) or 'Unchanged'} to {_date_value(finish) or 'Unchanged'}"


def _date_value(value: date | None) -> str:
    return value.isoformat() if value else ""


def _datetime_label(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else ""


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


__all__ = ["serialize_finance_change_workspace"]
