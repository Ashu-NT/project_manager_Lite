from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_dependency_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.dependency_id,
        title=f"{item.predecessor_project_name} -> {item.successor_project_name}",
        status_label=item.pressure_label,
        subtitle=item.dependency_type_label,
        supporting_text=(
            f"Predecessor {item.predecessor_project_status_label} | "
            f"Successor {item.successor_project_status_label}"
        ),
        meta_text=item.summary or f"Created: {item.created_at_label}",
        can_primary_action=True,
        can_secondary_action=False,
        state={
            "dependencyId": item.dependency_id,
            "predecessorProjectId": item.predecessor_project_id,
            "successorProjectId": item.successor_project_id,
        },
    )
