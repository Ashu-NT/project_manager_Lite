from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
)

from .record_mappers import build_cost_state

def build_detail_view_model(cost: Any) -> FinancialsDetailViewModel:
    if cost is None:
        return FinancialsDetailViewModel(
            title="No cost item selected",
            empty_state="Select a cost item to inspect financial detail or adjust the entry.",
        )
    state = build_cost_state(cost)
    return FinancialsDetailViewModel(
        id=cost.id,
        title=cost.description,
        status_label=cost.cost_type_label,
        subtitle=cost.task_name,
        description=(
            "Track planned, committed, and actual amounts for this selected cost line."
        ),
        fields=(
            FinancialsDetailFieldViewModel(
                label="Planned",
                value=cost.planned_amount_label,
                supporting_text="Baseline expected amount.",
            ),
            FinancialsDetailFieldViewModel(
                label="Forecast",
                value=cost.forecast_amount_label,
                supporting_text="Effective forecast (manual override or planned fallback).",
            ),
            FinancialsDetailFieldViewModel(
                label="Committed",
                value=cost.committed_amount_label,
                supporting_text="Committed commercial exposure.",
            ),
            FinancialsDetailFieldViewModel(
                label="Actual",
                value=cost.actual_amount_label,
                supporting_text="Actual recognized spend.",
            ),
            FinancialsDetailFieldViewModel(
                label="Commitment",
                value=cost.commitment_status_label,
                supporting_text="Purchase order lifecycle status.",
            ),
            FinancialsDetailFieldViewModel(
                label="Task",
                value=cost.task_name,
            ),
            FinancialsDetailFieldViewModel(
                label="Vendor ref",
                value=cost.vendor_reference or "Not set",
            ),
            FinancialsDetailFieldViewModel(
                label="Incurred date",
                value=cost.incurred_date_label,
            ),
            FinancialsDetailFieldViewModel(
                label="Version",
                value=str(cost.version),
            ),
        ),
        state=state,
    )
