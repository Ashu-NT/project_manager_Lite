from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_signed_money,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_percent,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_heatmap_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.project_id,
        title=item.project_name,
        status_label=item.pressure_label,
        subtitle=str(item.project_status or "").replace("_", " ").title(),
        supporting_text=(
            f"Late {item.late_tasks} | Critical {item.critical_tasks} | "
            f"Peak util {format_percent(item.peak_utilization_percent)}"
        ),
        meta_text=f"Cost variance {format_signed_money(item.cost_variance)}",
        can_primary_action=False,
        can_secondary_action=False,
        state={"projectId": item.project_id},
    )
