from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_scenario_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Scenario",
        subtitle=(
            f"Budget limit: {item.budget_limit_label} | Capacity limit: {item.capacity_limit_label}"
        ),
        supporting_text=(
            f"Projects: {len(item.project_ids)} | Intake items: {len(item.intake_item_ids)}"
        ),
        meta_text=item.notes or f"Created: {item.created_at_label}",
        can_primary_action=False,
        can_secondary_action=False,
        state={"scenarioId": item.id, "projectIds": list(item.project_ids)},
    )
