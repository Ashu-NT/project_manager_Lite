from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceReliabilityService,
    MaintenanceSystemService,
)
from src.core.modules.maintenance.api.desktop.dashboard.models import (
    MaintenanceDashboardMetricDescriptor,
    MaintenanceDashboardOverviewDescriptor,
    MaintenanceDashboardSnapshotDescriptor,
    MaintenanceDashboardWindowOptionDescriptor,
)
from src.core.modules.maintenance.api.desktop.dashboard.serializers import (
    serialize_backlog_row,
    serialize_recurring_row,
    serialize_root_cause_row,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_location_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.platform.site import SiteService

_WINDOW_CHOICES = (30, 60, 90, 180, 365)
_SUMMARY_SUPPORTING_TEXT = {
    "Open work orders": "Current backlog",
    "In progress work orders": "Active execution",
    "Overdue work orders": "Past planned finish",
    "Completed in window": "Finished in selected window",
    "Open downtime events": "Unresolved downtime records",
    "Downtime minutes": "Selected window total",
    "MTTR hours": "Mean time to repair",
    "MTBF hours": "Mean time between failures",
}


class MaintenanceDashboardDesktopApi:
    def __init__(
        self,
        *,
        reliability_service: MaintenanceReliabilityService | None = None,
        site_service: SiteService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        location_service: MaintenanceLocationService | None = None,
        system_service: MaintenanceSystemService | None = None,
    ) -> None:
        self._reliability_service = reliability_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._location_service = location_service
        self._system_service = system_service

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceSiteOptionDescriptor, ...]:
        if self._site_service is None:
            return ()
        rows = sorted(
            self._site_service.list_sites(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "site_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_site_option(row) for row in rows)

    def list_asset_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceAssetOptionDescriptor, ...]:
        if self._asset_service is None:
            return ()
        rows = sorted(
            self._asset_service.list_assets(active_only=active_only, site_id=site_id),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "asset_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_asset_option(row) for row in rows)

    def list_system_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceSystemOptionDescriptor, ...]:
        if self._system_service is None:
            return ()
        rows = sorted(
            self._system_service.list_systems(active_only=active_only, site_id=site_id),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "system_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_system_option(row) for row in rows)

    def list_location_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceLocationOptionDescriptor, ...]:
        if self._location_service is None:
            return ()
        rows = sorted(
            self._location_service.list_locations(active_only=active_only, site_id=site_id),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "location_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_location_option(row) for row in rows)

    def list_window_options(self) -> tuple[MaintenanceDashboardWindowOptionDescriptor, ...]:
        return tuple(
            MaintenanceDashboardWindowOptionDescriptor(value=days, label=f"{days} days")
            for days in _WINDOW_CHOICES
        )

    def build_empty_overview(self) -> MaintenanceDashboardOverviewDescriptor:
        return MaintenanceDashboardOverviewDescriptor(
            title="Maintenance Dashboard",
            subtitle=(
                "See backlog pressure, downtime signals, root causes, and recurring "
                "failures from the first maintenance analytics seam."
            ),
            metrics=tuple(
                MaintenanceDashboardMetricDescriptor(label, "0", supporting_text)
                for label, supporting_text in _SUMMARY_SUPPORTING_TEXT.items()
            ),
        )

    def build_snapshot(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 90,
    ) -> MaintenanceDashboardSnapshotDescriptor:
        site_options = self.list_sites(active_only=None)
        selected_site_id = self._resolve_option_value(site_id, site_options)
        asset_options = self.list_asset_options(active_only=True, site_id=selected_site_id or None)
        selected_asset_id = self._resolve_option_value(asset_id, asset_options)
        system_options = self.list_system_options(active_only=True, site_id=selected_site_id or None)
        selected_system_id = self._resolve_option_value(system_id, system_options)
        location_options = self.list_location_options(active_only=True, site_id=selected_site_id or None)
        selected_location_id = self._resolve_option_value(location_id, location_options)
        window_options = self.list_window_options()
        selected_days = self._resolve_days(days)

        if self._reliability_service is None:
            return MaintenanceDashboardSnapshotDescriptor(
                overview=self.build_empty_overview(),
                site_options=site_options,
                selected_site_id=selected_site_id,
                asset_options=asset_options,
                selected_asset_id=selected_asset_id,
                system_options=system_options,
                selected_system_id=selected_system_id,
                location_options=location_options,
                selected_location_id=selected_location_id,
                window_options=window_options,
                selected_days=selected_days,
                empty_state="Maintenance dashboard desktop API is not connected.",
            )

        dashboard = self._reliability_service.build_reliability_dashboard(
            site_id=selected_site_id or None,
            asset_id=selected_asset_id or None,
            system_id=selected_system_id or None,
            location_id=selected_location_id or None,
            days=selected_days,
            limit=10,
        )
        overview = MaintenanceDashboardOverviewDescriptor(
            title="Maintenance Dashboard",
            subtitle=(
                "See backlog pressure, downtime signals, root causes, and recurring "
                "failures from the first maintenance analytics seam."
            ),
            metrics=tuple(
                MaintenanceDashboardMetricDescriptor(
                    str(getattr(metric, "label", "") or "-"),
                    str(getattr(metric, "value", 0)),
                    _SUMMARY_SUPPORTING_TEXT.get(str(getattr(metric, "label", "") or ""), ""),
                )
                for metric in getattr(dashboard, "summary", ())
            ),
        )
        backlog_rows = tuple(
            [serialize_backlog_row(group="status", metric=metric) for metric in getattr(dashboard, "backlog_by_status", ())]
            + [serialize_backlog_row(group="priority", metric=metric) for metric in getattr(dashboard, "backlog_by_priority", ())]
        )
        root_cause_rows = tuple(
            serialize_root_cause_row(row) for row in getattr(dashboard, "top_root_causes", ())
        )
        recurring_rows = tuple(
            serialize_recurring_row(row) for row in getattr(dashboard, "recurring_failures", ())
        )
        has_content = any((backlog_rows, root_cause_rows, recurring_rows))
        return MaintenanceDashboardSnapshotDescriptor(
            overview=overview,
            site_options=site_options,
            selected_site_id=selected_site_id,
            asset_options=asset_options,
            selected_asset_id=selected_asset_id,
            system_options=system_options,
            selected_system_id=selected_system_id,
            location_options=location_options,
            selected_location_id=selected_location_id,
            window_options=window_options,
            selected_days=selected_days,
            backlog_rows=backlog_rows,
            root_cause_rows=root_cause_rows,
            recurring_rows=recurring_rows,
            empty_state="" if has_content else "No dashboard analytics match the current filters.",
        )

    @staticmethod
    def _resolve_option_value(value: str | None, options) -> str:
        normalized = str(value or "").strip()
        if normalized and any(option.value == normalized for option in options):
            return normalized
        return ""

    @staticmethod
    def _resolve_days(value: int | str | None) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError):
            return 90
        return resolved if resolved in _WINDOW_CHOICES else 90


def build_maintenance_dashboard_desktop_api(
    *,
    reliability_service: MaintenanceReliabilityService | None = None,
    site_service: SiteService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    location_service: MaintenanceLocationService | None = None,
    system_service: MaintenanceSystemService | None = None,
) -> MaintenanceDashboardDesktopApi:
    return MaintenanceDashboardDesktopApi(
        reliability_service=reliability_service,
        site_service=site_service,
        asset_service=asset_service,
        location_service=location_service,
        system_service=system_service,
    )


__all__ = [
    "MaintenanceDashboardDesktopApi",
    "build_maintenance_dashboard_desktop_api",
]
