from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenancePlannerDesktopApi,
    build_maintenance_planner_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerMaterialRiskRowViewModel,
    MaintenancePlannerMetricViewModel,
    MaintenancePlannerOptionViewModel,
    MaintenancePlannerOverviewViewModel,
    MaintenancePlannerPreventiveRowViewModel,
    MaintenancePlannerRecurringRowViewModel,
    MaintenancePlannerRequestRowViewModel,
    MaintenancePlannerWorkOrderRowViewModel,
    MaintenancePlannerWorkspaceViewModel,
)


def _option(value: str, label: str) -> MaintenancePlannerOptionViewModel:
    return MaintenancePlannerOptionViewModel(value=value, label=label)


class MaintenancePlannerWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenancePlannerDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_planner_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        request_queue: str = "",
        work_order_queue: str = "",
        search_text: str = "",
    ) -> MaintenancePlannerWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(
            site_id=site_id or None,
            asset_id=asset_id or None,
            system_id=system_id or None,
            request_queue=request_queue,
            work_order_queue=work_order_queue,
            search_text=search_text,
        )
        return MaintenancePlannerWorkspaceViewModel(
            overview=MaintenancePlannerOverviewViewModel(
                title=snapshot.overview.title,
                subtitle=snapshot.overview.subtitle,
                metrics=tuple(
                    MaintenancePlannerMetricViewModel(
                        label=metric.label,
                        value=metric.value,
                        supporting_text=metric.supporting_text,
                    )
                    for metric in snapshot.overview.metrics
                ),
            ),
            site_options=(_option("all", "All sites"),)
            + tuple(_option(option.value, option.label) for option in snapshot.site_options),
            selected_site_filter=snapshot.selected_site_id or "all",
            asset_options=(_option("all", "All assets"),)
            + tuple(
                _option(option.value, option.label)
                for option in snapshot.asset_options
            ),
            selected_asset_filter=snapshot.selected_asset_id or "all",
            system_options=(_option("all", "All systems"),)
            + tuple(
                _option(option.value, option.label)
                for option in snapshot.system_options
            ),
            selected_system_filter=snapshot.selected_system_id or "all",
            request_queue_options=tuple(
                _option(option.value, option.label)
                for option in snapshot.request_queue_options
            ),
            selected_request_queue=snapshot.selected_request_queue,
            work_order_queue_options=tuple(
                _option(option.value, option.label)
                for option in snapshot.work_order_queue_options
            ),
            selected_work_order_queue=snapshot.selected_work_order_queue,
            search_text=snapshot.search_text,
            request_rows=tuple(
                MaintenancePlannerRequestRowViewModel(
                    id=row.id,
                    request_label=row.request_label,
                    anchor_label=row.anchor_label,
                    status_label=row.status_label,
                    priority_label=row.priority_label,
                )
                for row in snapshot.request_rows
            ),
            work_order_rows=tuple(
                MaintenancePlannerWorkOrderRowViewModel(
                    id=row.id,
                    work_order_label=row.work_order_label,
                    work_order_type_label=row.work_order_type_label,
                    status_label=row.status_label,
                    priority_label=row.priority_label,
                    plan_window_label=row.plan_window_label,
                )
                for row in snapshot.work_order_rows
            ),
            material_rows=tuple(
                MaintenancePlannerMaterialRiskRowViewModel(
                    id=row.id,
                    work_order_id=row.work_order_id,
                    work_order_label=row.work_order_label,
                    material_label=row.material_label,
                    procurement_status_label=row.procurement_status_label,
                    quantity_label=row.quantity_label,
                    storeroom_label=row.storeroom_label,
                )
                for row in snapshot.material_rows
            ),
            preventive_rows=tuple(
                MaintenancePlannerPreventiveRowViewModel(
                    plan_id=row.plan_id,
                    plan_label=row.plan_label,
                    anchor_label=row.anchor_label,
                    due_state_label=row.due_state_label,
                    due_reason=row.due_reason,
                    generation_target_label=row.generation_target_label,
                    trigger_label=row.trigger_label,
                    next_due_label=row.next_due_label,
                    is_due_soon=row.is_due_soon,
                )
                for row in snapshot.preventive_rows
            ),
            recurring_rows=tuple(
                MaintenancePlannerRecurringRowViewModel(
                    anchor_id=row.anchor_id,
                    anchor_label=row.anchor_label,
                    failure_name=row.failure_name,
                    leading_root_cause_name=row.leading_root_cause_name,
                    occurrence_count=row.occurrence_count,
                    open_work_orders=row.open_work_orders,
                    sensor_exception_count=row.sensor_exception_count,
                )
                for row in snapshot.recurring_rows
            ),
            empty_state=snapshot.empty_state,
        )


__all__ = ["MaintenancePlannerWorkspacePresenter"]
