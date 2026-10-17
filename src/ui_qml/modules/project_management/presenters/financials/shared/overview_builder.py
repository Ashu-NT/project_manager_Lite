from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.overview.models.overview_facts import (
    FinanceOverviewFacts,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsMetricViewModel,
    FinancialsOverviewViewModel,
)


def build_overview(
    *,
    project_options: Any,
    selected_project_id: str,
    snapshot: FinanceOverviewFacts | None,
    selected_project_label: str = "",
) -> FinancialsOverviewViewModel:
    currency = snapshot.currency_code if snapshot else None
    has_budget = bool(snapshot and snapshot.approved_budget_id)

    def amount(value: Decimal | None, unavailable: str = "Not available") -> str:
        return unavailable if value is None else format_money(value, currency)

    project_label = next(
        (
            option.label
            for option in project_options
            if option.value == selected_project_id
        ),
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
                value=amount(snapshot.approved_budget)
                if has_budget and snapshot
                else ("Not approved" if snapshot else "Not available"),
                supporting_text=(
                    f"Approved revision {snapshot.approved_budget_revision}"
                    if snapshot is not None
                    and snapshot.approved_budget_revision is not None
                    else "No approved budget revision."
                ),
            ),
            FinancialsMetricViewModel(
                label="Open commitments",
                value=amount(snapshot.open_commitment if snapshot else None),
                supporting_text="Unmatched Procurement commitment balance.",
            ),
            FinancialsMetricViewModel(
                label="Actual",
                value=amount(snapshot.posted_actual if snapshot else None),
                supporting_text="Net posted actuals, including reversal entries.",
            ),
            FinancialsMetricViewModel(
                label="Available",
                value=amount(snapshot.available_after_commitment if snapshot else None),
                supporting_text="Approved budget less posted actuals and open commitments.",
            ),
            FinancialsMetricViewModel(
                label="Forecast ETC",
                value=amount(
                    snapshot.forecast_etc if snapshot else None, "Not approved"
                ),
                supporting_text=(
                    f"Approved revision {snapshot.approved_forecast_revision} as of "
                    f"{snapshot.approved_forecast_as_of.isoformat()}"
                    if snapshot is not None
                    and snapshot.approved_forecast_revision is not None
                    and snapshot.approved_forecast_as_of is not None
                    else "No approved forecast at the current as-of date."
                ),
            ),
            FinancialsMetricViewModel(
                label="EAC",
                value=amount(snapshot.estimate_at_completion if snapshot else None),
                supporting_text="Posted actual plus approved forecast ETC.",
            ),
            FinancialsMetricViewModel(
                label="Budget headroom",
                value=amount(snapshot.budget_headroom if snapshot else None),
                supporting_text="Approved budget less estimate at completion. This is not EVM VAC.",
            ),
        ),
    )
