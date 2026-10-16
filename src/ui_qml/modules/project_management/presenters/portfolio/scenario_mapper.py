from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_datetime,
    format_percent,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_scenario_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Scenario",
        subtitle=(
            f"Budget limit: {format_money(item.budget_limit, fallback="No budget limit")} | Capacity limit: {format_percent(item.capacity_limit_percent, fallback="No capacity limit")}"
        ),
        supporting_text=(
            f"Projects: {len(item.project_ids)} | Intake items: {len(item.intake_item_ids)}"
        ),
        meta_text=item.notes or f"Created: {format_datetime(item.created_at)}",
        can_primary_action=False,
        can_secondary_action=False,
        state={"scenarioId": item.id, "projectIds": list(item.project_ids)},
    )
