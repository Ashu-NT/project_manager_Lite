from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_recent_action_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=f"{item.occurred_at_label}-{item.project_name}-{item.action_label}",
        title=item.action_label,
        status_label=item.project_name,
        subtitle=f"{item.actor_username} | {item.occurred_at_label}",
        supporting_text=item.summary,
        meta_text=f"{item.actor_username} | {item.occurred_at_label}",
        can_primary_action=False,
        can_secondary_action=False,
    )
