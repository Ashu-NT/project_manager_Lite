from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.api.desktop._support import format_enum_label
from src.core.modules.maintenance.api.desktop.assets.serializers import (
    asset_label,
    component_label,
    location_label,
    system_label,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceComponentOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_component_option,
    serialize_location_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.modules.maintenance.api.desktop.work_requests.models import (
    MaintenancePriorityDescriptor,
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkRequestDesktopDto,
    MaintenanceWorkRequestSourceTypeDescriptor,
    MaintenanceWorkRequestStatusDescriptor,
    MaintenanceWorkRequestUpdateCommand,
)
from src.core.modules.maintenance.api.desktop.work_requests.serializers import (
    serialize_work_request,
    timestamp_sort_key,
)
from src.core.modules.maintenance.domain import (
    MaintenancePriority,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
)
from src.core.platform.org import SiteService


class MaintenanceWorkRequestsDesktopApi:
    def __init__(
        self,
        *,
        work_request_service: MaintenanceWorkRequestService | None = None,
        site_service: SiteService | None = None,
        location_service: MaintenanceLocationService | None = None,
        system_service: MaintenanceSystemService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        component_service: MaintenanceAssetComponentService | None = None,
    ) -> None:
        self._work_request_service = work_request_service
        self._site_service = site_service
        self._location_service = location_service
        self._system_service = system_service
        self._asset_service = asset_service
        self._component_service = component_service

    def list_priorities(self) -> tuple[MaintenancePriorityDescriptor, ...]:
        return tuple(
            MaintenancePriorityDescriptor(
                value=priority.value,
                label=format_enum_label(priority.value),
            )
            for priority in MaintenancePriority
        )

    def list_source_types(self) -> tuple[MaintenanceWorkRequestSourceTypeDescriptor, ...]:
        return tuple(
            MaintenanceWorkRequestSourceTypeDescriptor(
                value=source_type.value,
                label=format_enum_label(source_type.value),
            )
            for source_type in MaintenanceWorkRequestSourceType
        )

    def list_statuses(self) -> tuple[MaintenanceWorkRequestStatusDescriptor, ...]:
        return tuple(
            MaintenanceWorkRequestStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in MaintenanceWorkRequestStatus
        )

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

    def list_location_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceLocationOptionDescriptor, ...]:
        service = self._require_location_service()
        rows = sorted(
            service.list_locations(active_only=active_only, site_id=site_id),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "location_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_location_option(row) for row in rows)

    def list_system_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
    ) -> tuple[MaintenanceSystemOptionDescriptor, ...]:
        service = self._require_system_service()
        rows = sorted(
            service.list_systems(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "system_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_system_option(row) for row in rows)

    def list_asset_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
    ) -> tuple[MaintenanceAssetOptionDescriptor, ...]:
        service = self._require_asset_service()
        rows = sorted(
            service.list_assets(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
                system_id=system_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "asset_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_asset_option(row) for row in rows)

    def list_component_options(
        self,
        *,
        active_only: bool | None = True,
        asset_id: str | None = None,
    ) -> tuple[MaintenanceComponentOptionDescriptor, ...]:
        service = self._require_component_service()
        rows = sorted(
            service.list_components(
                active_only=active_only,
                asset_id=asset_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "component_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_component_option(row) for row in rows)

    def list_work_requests(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        requested_by_user_id: str | None = None,
        triaged_by_user_id: str | None = None,
    ) -> tuple[MaintenanceWorkRequestDesktopDto, ...]:
        service = self._require_work_request_service()
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = self._system_label_lookup(active_only=None)
        asset_lookup = self._asset_label_lookup(active_only=None)
        component_lookup = self._component_label_lookup(active_only=None)
        rows = sorted(
            service.list_work_requests(
                site_id=site_id,
                asset_id=asset_id,
                component_id=component_id,
                system_id=system_id,
                location_id=location_id,
                status=status,
                priority=priority,
                requested_by_user_id=requested_by_user_id,
                triaged_by_user_id=triaged_by_user_id,
            ),
            key=lambda row: (
                timestamp_sort_key(getattr(row, "requested_at", None)),
                str(getattr(row, "work_request_code", "") or "").casefold(),
            ),
            reverse=True,
        )
        return tuple(
            serialize_work_request(
                row,
                site_lookup=site_lookup,
                location_lookup=location_lookup,
                system_lookup=system_lookup,
                asset_lookup=asset_lookup,
                component_lookup=component_lookup,
            )
            for row in rows
        )

    def create_work_request(
        self,
        command: MaintenanceWorkRequestCreateCommand,
    ) -> MaintenanceWorkRequestDesktopDto:
        service = self._require_work_request_service()
        row = service.create_work_request(
            site_id=command.site_id,
            work_request_code=command.work_request_code,
            source_type=command.source_type,
            source_id=command.source_id,
            source_plan_task_ids=command.source_plan_task_ids,
            request_type=command.request_type,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            location_id=command.location_id,
            title=command.title,
            description=command.description,
            priority=command.priority,
            failure_symptom_code=command.failure_symptom_code,
            safety_risk_level=command.safety_risk_level,
            production_impact_level=command.production_impact_level,
            notes=command.notes,
        )
        return self._serialize_work_request_by_id(row.id)

    def update_work_request(
        self,
        command: MaintenanceWorkRequestUpdateCommand,
    ) -> MaintenanceWorkRequestDesktopDto:
        service = self._require_work_request_service()
        row = service.update_work_request(
            command.work_request_id,
            work_request_code=command.work_request_code,
            request_type=command.request_type,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            location_id=command.location_id,
            title=command.title,
            description=command.description,
            priority=command.priority,
            status=command.status,
            failure_symptom_code=command.failure_symptom_code,
            safety_risk_level=command.safety_risk_level,
            production_impact_level=command.production_impact_level,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_work_request_by_id(row.id)

    def _require_work_request_service(self) -> MaintenanceWorkRequestService:
        if self._work_request_service is None:
            raise RuntimeError("Maintenance work-requests desktop API is not connected.")
        return self._work_request_service

    def _require_location_service(self) -> MaintenanceLocationService:
        if self._location_service is None:
            raise RuntimeError("Maintenance work-requests desktop API is not connected.")
        return self._location_service

    def _require_system_service(self) -> MaintenanceSystemService:
        if self._system_service is None:
            raise RuntimeError("Maintenance work-requests desktop API is not connected.")
        return self._system_service

    def _require_asset_service(self) -> MaintenanceAssetService:
        if self._asset_service is None:
            raise RuntimeError("Maintenance work-requests desktop API is not connected.")
        return self._asset_service

    def _require_component_service(self) -> MaintenanceAssetComponentService:
        if self._component_service is None:
            raise RuntimeError("Maintenance work-requests desktop API is not connected.")
        return self._component_service

    def _serialize_work_request_by_id(
        self,
        work_request_id: str,
    ) -> MaintenanceWorkRequestDesktopDto:
        row = self._require_work_request_service().get_work_request(work_request_id)
        return serialize_work_request(
            row,
            site_lookup=self._site_lookup(active_only=None),
            location_lookup=self._location_label_lookup(active_only=None),
            system_lookup=self._system_label_lookup(active_only=None),
            asset_lookup=self._asset_label_lookup(active_only=None),
            component_lookup=self._component_label_lookup(active_only=None),
        )

    def _site_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_sites(active_only=active_only)
        }

    def _location_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: location_label(row)
            for row in self._require_location_service().list_locations(active_only=active_only)
        }

    def _system_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: system_label(row)
            for row in self._require_system_service().list_systems(active_only=active_only)
        }

    def _asset_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: asset_label(row)
            for row in self._require_asset_service().list_assets(active_only=active_only)
        }

    def _component_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: component_label(row)
            for row in self._require_component_service().list_components(active_only=active_only)
        }


def build_maintenance_work_requests_desktop_api(
    *,
    work_request_service: MaintenanceWorkRequestService | None = None,
    site_service: SiteService | None = None,
    location_service: MaintenanceLocationService | None = None,
    system_service: MaintenanceSystemService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    component_service: MaintenanceAssetComponentService | None = None,
) -> MaintenanceWorkRequestsDesktopApi:
    return MaintenanceWorkRequestsDesktopApi(
        work_request_service=work_request_service,
        site_service=site_service,
        location_service=location_service,
        system_service=system_service,
        asset_service=asset_service,
        component_service=component_service,
    )


__all__ = [
    "MaintenanceWorkRequestsDesktopApi",
    "build_maintenance_work_requests_desktop_api",
]
