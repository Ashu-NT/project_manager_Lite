from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceDashboardDesktopApi,
    build_maintenance_dashboard_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardBacklogRowViewModel,
    MaintenanceDashboardOverviewViewModel,
    MaintenanceDashboardRecurringRowViewModel,
    MaintenanceDashboardRootCauseRowViewModel,
    MaintenanceDashboardWorkspaceViewModel,
    MaintenanceMetricViewModel,
    MaintenanceOptionViewModel,
)


def _option(value: str, label: str) -> MaintenanceOptionViewModel:
    return MaintenanceOptionViewModel(value=value, label=label)


class MaintenanceDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_dashboard_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 90,
    ) -> MaintenanceDashboardWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(
            site_id=site_id or None,
            asset_id=asset_id or None,
            system_id=system_id or None,
            location_id=location_id or None,
            days=days,
        )
        return MaintenanceDashboardWorkspaceViewModel(
            overview=MaintenanceDashboardOverviewViewModel(
                title=snapshot.overview.title,
                subtitle=snapshot.overview.subtitle,
                metrics=tuple(
                    MaintenanceMetricViewModel(
                        label=metric.label,
                        value=metric.value,
                        supporting_text=metric.supporting_text,
                    )
                    for metric in snapshot.overview.metrics
                ),
            ),
            site_options=(_option("all", "All sites"),)
            + tuple(
                _option(option.value, option.label)
                for option in snapshot.site_options
            ),
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
            location_options=(_option("all", "All locations"),)
            + tuple(
                _option(option.value, option.label)
                for option in snapshot.location_options
            ),
            selected_location_filter=snapshot.selected_location_id or "all",
            window_options=tuple(
                _option(str(option.value), option.label)
                for option in snapshot.window_options
            ),
            selected_days_filter=str(snapshot.selected_days),
            backlog_rows=tuple(
                MaintenanceDashboardBacklogRowViewModel(
                    group=row.group,
                    label=row.label,
                    value=row.value,
                )
                for row in snapshot.backlog_rows
            ),
            root_cause_rows=tuple(
                MaintenanceDashboardRootCauseRowViewModel(
                    failure_name=row.failure_name,
                    root_cause_name=row.root_cause_name,
                    work_order_count=row.work_order_count,
                    total_downtime_minutes=row.total_downtime_minutes,
                    latest_occurrence_at_label=row.latest_occurrence_at_label,
                    open_work_orders=row.open_work_orders,
                )
                for row in snapshot.root_cause_rows
            ),
            recurring_rows=tuple(
                MaintenanceDashboardRecurringRowViewModel(
                    anchor_label=row.anchor_label,
                    failure_name=row.failure_name,
                    leading_root_cause_name=row.leading_root_cause_name,
                    occurrence_count=row.occurrence_count,
                    open_work_orders=row.open_work_orders,
                    total_downtime_minutes=row.total_downtime_minutes,
                    mean_interval_hours_label=row.mean_interval_hours_label,
                )
                for row in snapshot.recurring_rows
            ),
            empty_state=snapshot.empty_state,
        )


__all__ = ["MaintenanceDashboardWorkspacePresenter"]
