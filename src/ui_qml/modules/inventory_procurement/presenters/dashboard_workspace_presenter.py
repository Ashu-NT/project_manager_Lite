from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementDashboardDesktopApi,
    build_inventory_procurement_dashboard_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardMetricViewModel,
    InventoryDashboardOverviewViewModel,
    InventoryDashboardRowViewModel,
    InventoryDashboardSectionViewModel,
    InventoryDashboardWorkspaceViewModel,
)


class InventoryDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_dashboard_desktop_api()

    def build_workspace_state(self) -> InventoryDashboardWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot()
        return InventoryDashboardWorkspaceViewModel(
            overview=InventoryDashboardOverviewViewModel(
                title=snapshot.title,
                subtitle=snapshot.subtitle,
                metrics=tuple(
                    InventoryDashboardMetricViewModel(
                        label=metric.label,
                        value=metric.value,
                        supporting_text=metric.supporting_text,
                    )
                    for metric in snapshot.metrics
                ),
            ),
            context_label=snapshot.context_label,
            sections=tuple(
                InventoryDashboardSectionViewModel(
                    title=section.title,
                    subtitle=section.subtitle,
                    empty_state=section.empty_state,
                    rows=tuple(
                        InventoryDashboardRowViewModel(
                            id=row.id,
                            title=row.title,
                            subtitle=row.subtitle,
                            status_label=row.status_label,
                            supporting_text=row.supporting_text,
                            meta_text=row.meta_text,
                            tone=row.tone,
                        )
                        for row in section.rows
                    ),
                )
                for section in snapshot.sections
            ),
            empty_state=snapshot.empty_state,
        )


__all__ = ["InventoryDashboardWorkspacePresenter"]
