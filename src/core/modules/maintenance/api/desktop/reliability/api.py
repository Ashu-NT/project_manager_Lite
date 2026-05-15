from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetService,
    MaintenanceFailureCodeService,
    MaintenanceLocationService,
    MaintenanceReliabilityService,
    MaintenanceSystemService,
)
from src.core.modules.maintenance.api.desktop.reliability.models import (
    MaintenanceReliabilityChoiceDescriptor,
    MaintenanceReliabilityMetricDescriptor,
    MaintenanceReliabilityOverviewDescriptor,
    MaintenanceReliabilitySnapshotDescriptor,
)
from src.core.modules.maintenance.api.desktop.reliability.serializers import (
    serialize_failure_symptom_option,
    serialize_insight_row,
    serialize_recurring_row,
    serialize_suggestion_row,
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
from src.core.platform.org import SiteService

_DAY_CHOICES = (30, 60, 90, 180, 365)
_LIMIT_CHOICES = (5, 10, 20, 50)
_THRESHOLD_CHOICES = (2, 3, 4, 5)


class MaintenanceReliabilityDesktopApi:
    def __init__(
        self,
        *,
        reliability_service: MaintenanceReliabilityService | None = None,
        failure_code_service: MaintenanceFailureCodeService | None = None,
        site_service: SiteService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        location_service: MaintenanceLocationService | None = None,
        system_service: MaintenanceSystemService | None = None,
    ) -> None:
        self._reliability_service = reliability_service
        self._failure_code_service = failure_code_service
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

    def list_failure_symptom_options(self) -> tuple:
        if self._failure_code_service is None:
            return ()
        rows = sorted(
            self._failure_code_service.list_failure_codes(active_only=True, code_type="SYMPTOM"),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "failure_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_failure_symptom_option(row) for row in rows)

    def list_days_options(self) -> tuple[MaintenanceReliabilityChoiceDescriptor, ...]:
        return tuple(
            MaintenanceReliabilityChoiceDescriptor(value=days, label=f"{days} days")
            for days in _DAY_CHOICES
        )

    def list_limit_options(self) -> tuple[MaintenanceReliabilityChoiceDescriptor, ...]:
        return tuple(
            MaintenanceReliabilityChoiceDescriptor(value=limit, label=f"Top {limit}")
            for limit in _LIMIT_CHOICES
        )

    def list_threshold_options(self) -> tuple[MaintenanceReliabilityChoiceDescriptor, ...]:
        return tuple(
            MaintenanceReliabilityChoiceDescriptor(
                value=threshold,
                label=f"{threshold}+ repeats",
            )
            for threshold in _THRESHOLD_CHOICES
        )

    def build_empty_overview(self) -> MaintenanceReliabilityOverviewDescriptor:
        return MaintenanceReliabilityOverviewDescriptor(
            title="Reliability",
            subtitle=(
                "Review recurring failures, root-cause clusters, and generated "
                "maintenance report packs from one workbench."
            ),
            metrics=(
                MaintenanceReliabilityMetricDescriptor("Suggestions", "0", "Failure-guided suggestions"),
                MaintenanceReliabilityMetricDescriptor("Root causes", "0", "Observed combinations"),
                MaintenanceReliabilityMetricDescriptor("Recurring patterns", "0", "Repeat reliability signals"),
            ),
        )

    def build_snapshot(
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
    ) -> MaintenanceReliabilitySnapshotDescriptor:
        site_options = self.list_sites(active_only=None)
        selected_site_id = self._resolve_option_value(site_id, site_options)
        asset_options = self.list_asset_options(active_only=True, site_id=selected_site_id or None)
        selected_asset_id = self._resolve_option_value(asset_id, asset_options)
        system_options = self.list_system_options(active_only=True, site_id=selected_site_id or None)
        selected_system_id = self._resolve_option_value(system_id, system_options)
        location_options = self.list_location_options(active_only=True, site_id=selected_site_id or None)
        selected_location_id = self._resolve_option_value(location_id, location_options)
        failure_symptom_options = self.list_failure_symptom_options()
        selected_failure_code = self._resolve_failure_code(failure_code, failure_symptom_options)
        days_options = self.list_days_options()
        selected_days = self._resolve_int_choice(days, _DAY_CHOICES, 90)
        limit_options = self.list_limit_options()
        selected_limit = self._resolve_int_choice(limit, _LIMIT_CHOICES, 20)
        threshold_options = self.list_threshold_options()
        selected_threshold = self._resolve_int_choice(threshold, _THRESHOLD_CHOICES, 2)

        if self._reliability_service is None:
            return MaintenanceReliabilitySnapshotDescriptor(
                overview=self.build_empty_overview(),
                site_options=site_options,
                selected_site_id=selected_site_id,
                asset_options=asset_options,
                selected_asset_id=selected_asset_id,
                system_options=system_options,
                selected_system_id=selected_system_id,
                location_options=location_options,
                selected_location_id=selected_location_id,
                failure_symptom_options=failure_symptom_options,
                selected_failure_code=selected_failure_code,
                days_options=days_options,
                selected_days=selected_days,
                limit_options=limit_options,
                selected_limit=selected_limit,
                threshold_options=threshold_options,
                selected_threshold=selected_threshold,
                empty_state="Maintenance reliability desktop API is not connected.",
            )

        suggestion_rows = ()
        if selected_failure_code:
            suggestion_rows = tuple(
                serialize_suggestion_row(row)
                for row in self._reliability_service.suggest_root_causes(
                    failure_code=selected_failure_code,
                    asset_id=selected_asset_id or None,
                    system_id=selected_system_id or None,
                    days=selected_days,
                    limit=selected_limit,
                )
            )
        root_cause_rows = tuple(
            serialize_insight_row(row)
            for row in self._reliability_service.list_root_cause_analysis(
                site_id=selected_site_id or None,
                asset_id=selected_asset_id or None,
                system_id=selected_system_id or None,
                location_id=selected_location_id or None,
                days=selected_days,
                limit=selected_limit,
            )
        )
        recurring_rows = tuple(
            serialize_recurring_row(row)
            for row in self._reliability_service.list_recurring_failure_patterns(
                site_id=selected_site_id or None,
                asset_id=selected_asset_id or None,
                system_id=selected_system_id or None,
                location_id=selected_location_id or None,
                days=selected_days,
                min_occurrences=selected_threshold,
                limit=selected_limit,
            )
        )
        overview = MaintenanceReliabilityOverviewDescriptor(
            title="Reliability",
            subtitle=(
                "Review recurring failures, root-cause clusters, and generated "
                "maintenance report packs from one workbench."
            ),
            metrics=(
                MaintenanceReliabilityMetricDescriptor(
                    "Suggestions",
                    str(len(suggestion_rows)),
                    "Failure-guided suggestions",
                ),
                MaintenanceReliabilityMetricDescriptor(
                    "Root causes",
                    str(len(root_cause_rows)),
                    "Observed combinations",
                ),
                MaintenanceReliabilityMetricDescriptor(
                    "Recurring patterns",
                    str(len(recurring_rows)),
                    "Repeat reliability signals",
                ),
            ),
        )
        has_content = any((suggestion_rows, root_cause_rows, recurring_rows))
        return MaintenanceReliabilitySnapshotDescriptor(
            overview=overview,
            site_options=site_options,
            selected_site_id=selected_site_id,
            asset_options=asset_options,
            selected_asset_id=selected_asset_id,
            system_options=system_options,
            selected_system_id=selected_system_id,
            location_options=location_options,
            selected_location_id=selected_location_id,
            failure_symptom_options=failure_symptom_options,
            selected_failure_code=selected_failure_code,
            days_options=days_options,
            selected_days=selected_days,
            limit_options=limit_options,
            selected_limit=selected_limit,
            threshold_options=threshold_options,
            selected_threshold=selected_threshold,
            suggestion_rows=suggestion_rows,
            root_cause_rows=root_cause_rows,
            recurring_rows=recurring_rows,
            empty_state="" if has_content else "No reliability analytics match the current filters.",
        )

    @staticmethod
    def _resolve_option_value(value: str | None, options) -> str:
        normalized = str(value or "").strip()
        if normalized and any(option.value == normalized for option in options):
            return normalized
        return ""

    @staticmethod
    def _resolve_failure_code(value: str | None, options) -> str:
        normalized = str(value or "").strip().upper()
        if normalized and any(option.value == normalized for option in options):
            return normalized
        return ""

    @staticmethod
    def _resolve_int_choice(value: int | str | None, choices, default: int) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError):
            return default
        return resolved if resolved in choices else default


def build_maintenance_reliability_desktop_api(
    *,
    reliability_service: MaintenanceReliabilityService | None = None,
    failure_code_service: MaintenanceFailureCodeService | None = None,
    site_service: SiteService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    location_service: MaintenanceLocationService | None = None,
    system_service: MaintenanceSystemService | None = None,
) -> MaintenanceReliabilityDesktopApi:
    return MaintenanceReliabilityDesktopApi(
        reliability_service=reliability_service,
        failure_code_service=failure_code_service,
        site_service=site_service,
        asset_service=asset_service,
        location_service=location_service,
        system_service=system_service,
    )


__all__ = [
    "MaintenanceReliabilityDesktopApi",
    "build_maintenance_reliability_desktop_api",
]
