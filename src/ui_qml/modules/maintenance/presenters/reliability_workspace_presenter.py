from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceReliabilityDesktopApi,
    build_maintenance_reliability_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceFailureSymptomOptionViewModel,
    MaintenanceReliabilityInsightRowViewModel,
    MaintenanceReliabilityMetricViewModel,
    MaintenanceReliabilityOptionViewModel,
    MaintenanceReliabilityOverviewViewModel,
    MaintenanceReliabilityRecurringRowViewModel,
    MaintenanceReliabilitySuggestionRowViewModel,
    MaintenanceReliabilityWorkspaceViewModel,
)


def _option(value: str, label: str) -> MaintenanceReliabilityOptionViewModel:
    return MaintenanceReliabilityOptionViewModel(value=value, label=label)


class MaintenanceReliabilityWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceReliabilityDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_reliability_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        failure_code: str | None = None,
        days: int = 90,
        limit: int = 20,
        threshold: int = 2,
    ) -> MaintenanceReliabilityWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(
            site_id=site_id or None,
            asset_id=asset_id or None,
            system_id=system_id or None,
            location_id=location_id or None,
            failure_code=failure_code or None,
            days=days,
            limit=limit,
            threshold=threshold,
        )
        return MaintenanceReliabilityWorkspaceViewModel(
            overview=MaintenanceReliabilityOverviewViewModel(
                title=snapshot.overview.title,
                subtitle=snapshot.overview.subtitle,
                metrics=tuple(
                    MaintenanceReliabilityMetricViewModel(
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
            failure_symptom_options=(
                MaintenanceFailureSymptomOptionViewModel(
                    value="all",
                    label="All failure symptoms",
                    failure_code="",
                    name="",
                    is_active=True,
                ),
            )
            + tuple(
                MaintenanceFailureSymptomOptionViewModel(
                    value=option.value,
                    label=option.label,
                    failure_code=option.failure_code,
                    name=option.name,
                    is_active=option.is_active,
                )
                for option in snapshot.failure_symptom_options
            ),
            selected_failure_code_filter=snapshot.selected_failure_code or "all",
            days_options=tuple(
                _option(str(option.value), option.label)
                for option in snapshot.days_options
            ),
            selected_days_filter=str(snapshot.selected_days),
            limit_options=tuple(
                _option(str(option.value), option.label)
                for option in snapshot.limit_options
            ),
            selected_limit_filter=str(snapshot.selected_limit),
            threshold_options=tuple(
                _option(str(option.value), option.label)
                for option in snapshot.threshold_options
            ),
            selected_threshold_filter=str(snapshot.selected_threshold),
            suggestion_rows=tuple(
                MaintenanceReliabilitySuggestionRowViewModel(
                    match_scope_label=row.match_scope_label,
                    root_cause_name=row.root_cause_name,
                    occurrence_count=row.occurrence_count,
                    total_downtime_minutes=row.total_downtime_minutes,
                    latest_occurrence_at_label=row.latest_occurrence_at_label,
                )
                for row in snapshot.suggestion_rows
            ),
            root_cause_rows=tuple(
                MaintenanceReliabilityInsightRowViewModel(
                    failure_name=row.failure_name,
                    root_cause_name=row.root_cause_name,
                    work_order_count=row.work_order_count,
                    total_downtime_minutes=row.total_downtime_minutes,
                    open_work_orders=row.open_work_orders,
                )
                for row in snapshot.root_cause_rows
            ),
            recurring_rows=tuple(
                MaintenanceReliabilityRecurringRowViewModel(
                    anchor_label=row.anchor_label,
                    failure_name=row.failure_name,
                    leading_root_cause_name=row.leading_root_cause_name,
                    occurrence_count=row.occurrence_count,
                    open_work_orders=row.open_work_orders,
                    mean_interval_hours_label=row.mean_interval_hours_label,
                )
                for row in snapshot.recurring_rows
            ),
            empty_state=snapshot.empty_state,
        )


__all__ = ["MaintenanceReliabilityWorkspacePresenter"]
