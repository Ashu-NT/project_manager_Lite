from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_heatmap_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.project_id,
        title=item.project_name,
        status_label=item.pressure_label,
        subtitle=item.project_status_label,
        supporting_text=(
            f"Late {item.late_tasks} | Critical {item.critical_tasks} | "
            f"Peak util {item.peak_utilization_label}"
        ),
        meta_text=f"Cost variance {item.cost_variance_label}",
        can_primary_action=False,
        can_secondary_action=False,
        state={"projectId": item.project_id},
    )
