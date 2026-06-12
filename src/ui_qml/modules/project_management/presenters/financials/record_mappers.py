from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsRecordViewModel,
)

from .formatters import format_amount, format_date_iso

def build_cost_state(cost: Any) -> dict[str, object]:
    return {
        "costId": cost.id,
        "projectId": cost.project_id,
        "taskId": cost.task_id or "",
        "taskName": cost.task_name or "",
        "costCode": getattr(cost, "code", "") or "",
        "description": cost.description,
        "plannedAmount": format_amount(cost.planned_amount),
        "plannedAmountLabel": cost.planned_amount_label,
        "forecastAmount": format_amount(cost.forecast_amount),
        "forecastAmountLabel": cost.forecast_amount_label,
        "committedAmount": format_amount(cost.committed_amount),
        "committedAmountLabel": cost.committed_amount_label,
        "actualAmount": format_amount(cost.actual_amount),
        "actualAmountLabel": cost.actual_amount_label,
        "commitmentStatus": cost.commitment_status,
        "commitmentStatusLabel": cost.commitment_status_label,
        "vendorReference": cost.vendor_reference or "",
        "costType": cost.cost_type,
        "currency": cost.currency_code or "",
        "incurredDate": format_date_iso(cost.incurred_date),
        "incurredDateLabel": cost.incurred_date_label,
        "version": cost.version,
    }

def to_cost_record(cost: Any) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=cost.id,
        title=cost.description,
        status_label=cost.cost_type_label,
        subtitle=cost.task_name,
        supporting_text=(
            f"Planned {cost.planned_amount_label} | "
            f"Committed {cost.committed_amount_label} | "
            f"Actual {cost.actual_amount_label}"
        ),
        meta_text=f"{cost.incurred_date_label} | {cost.currency_code or 'Default currency'}",
        state=build_cost_state(cost),
    )
