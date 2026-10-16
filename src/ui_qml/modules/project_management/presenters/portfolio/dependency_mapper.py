from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.dependency_presentation import (
    dependency_type_label,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_datetime,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_dependency_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.dependency_id,
        title=f"{item.predecessor_project_name} -> {item.successor_project_name}",
        status_label=item.pressure_label,
        subtitle=dependency_type_label(item.dependency_type),
        supporting_text=(
            f"Predecessor {str(item.predecessor_project_status or "").replace("_", " ").title()} | "
            f"Successor {str(item.successor_project_status or "").replace("_", " ").title()}"
        ),
        meta_text=item.summary or f"Created: {format_datetime(item.created_at)}",
        can_primary_action=True,
        can_secondary_action=False,
        state={
            "dependencyId": item.dependency_id,
            "predecessorProjectId": item.predecessor_project_id,
            "successorProjectId": item.successor_project_id,
        },
    )
