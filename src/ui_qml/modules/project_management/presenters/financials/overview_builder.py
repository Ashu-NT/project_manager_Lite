from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsMetricViewModel,
    FinancialsOverviewViewModel,
)

def build_overview(
    *,
    project_options: Any,
    selected_project_id: str,
    snapshot: Any,
    selected_project_label: str = "",
) -> FinancialsOverviewViewModel:
    project_label = next(
        (option.label for option in project_options if option.value == selected_project_id),
        selected_project_label or "Financials",
    )
    return FinancialsOverviewViewModel(
        title="Financials",
        subtitle=(
            f"{project_label} budget, cost, commitment, and forecast control."
            if selected_project_id
            else "Select a project to review cost control and finance exposure."
        ),
        metrics=(
            FinancialsMetricViewModel(
                label="Budget",
                value=snapshot.budget_label,
                supporting_text=(
                    f"Approved revision {snapshot.approved_budget_revision}"
                    if snapshot.approved_budget_revision is not None
                    else "No approved budget revision."
                ),
            ),
            FinancialsMetricViewModel(
                label="Open commitments",
                value=snapshot.committed_label,
                supporting_text="Unmatched Procurement commitment balance.",
            ),
            FinancialsMetricViewModel(
                label="Actual",
                value=snapshot.actual_label,
                supporting_text="Net posted actuals, including reversal entries.",
            ),
            FinancialsMetricViewModel(
                label="Available",
                value=snapshot.available_label,
                supporting_text="Approved budget less posted actuals and open commitments.",
            ),
            FinancialsMetricViewModel(
                label="Forecast ETC",
                value=snapshot.forecast_etc_label,
                supporting_text=(
                    f"Approved revision {snapshot.approved_forecast_revision} as of "
                    f"{snapshot.approved_forecast_as_of.isoformat()}"
                    if snapshot.approved_forecast_revision is not None
                    and snapshot.approved_forecast_as_of is not None
                    else "No approved forecast at the current as-of date."
                ),
            ),
            FinancialsMetricViewModel(
                label="EAC",
                value=snapshot.estimate_at_completion_label,
                supporting_text="Posted actual plus approved forecast ETC.",
            ),
            FinancialsMetricViewModel(
                label="VAC",
                value=snapshot.variance_at_completion_label,
                supporting_text="Approved budget less estimate at completion.",
            ),
        ),
    )
