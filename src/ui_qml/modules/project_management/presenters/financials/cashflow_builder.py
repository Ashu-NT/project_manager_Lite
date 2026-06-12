from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)

def build_cashflow_collection(snapshot: Any) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Cashflow",
        subtitle="Forecast, actuals, and exposure grouped by period.",
        empty_state="No finance periods are available for the selected project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=row.period_key,
                title=row.period_key,
                status_label=row.forecast_label,
                subtitle=f"Planned {row.planned_label} | Committed {row.committed_label}",
                supporting_text=f"Actual {row.actual_label} | Exposure {row.exposure_label}",
                meta_text="Monthly period rollup",
                can_primary_action=False,
                can_secondary_action=False,
                state={},
            )
            for row in snapshot.cashflow
        ),
    )
