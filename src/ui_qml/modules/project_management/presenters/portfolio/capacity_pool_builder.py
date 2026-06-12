from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
    PortfolioRecordViewModel,
)


def build_capacity_pool_view_model(
    desktop_api: ProjectManagementPortfolioDesktopApi,
) -> PortfolioCollectionViewModel:
    dtos = desktop_api.build_capacity_pool()
    items = tuple(
        PortfolioRecordViewModel(
            id=dto.resource_id,
            title=dto.resource_name,
            status_label=f"{dto.peak_load_percent:.0f}%",
            subtitle=f"Avg {dto.average_load_percent:.0f}% | {'Overloaded' if dto.overloaded else 'OK'}",
            supporting_text=(
                ", ".join(dto.demand_entries) if dto.demand_entries else "No active assignments"
            ),
            meta_text="Overloaded" if dto.overloaded else "Available",
            can_primary_action=False,
            can_secondary_action=False,
            state={"overloaded": dto.overloaded, "peakLoadPercent": dto.peak_load_percent},
        )
        for dto in dtos
    )
    return PortfolioCollectionViewModel(
        title="Capacity Pool",
        subtitle="Resource demand vs capacity across all active projects (90-day outlook).",
        empty_state="No resource pool data available. Assign resources to tasks to see capacity demand.",
        items=items,
    )
