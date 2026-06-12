from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.api.desktop._support import (
    decimal_value,
    format_enum_label,
    parse_datetime_text,
)
from src.core.modules.maintenance.api.desktop.assets.serializers import (
    asset_label,
    component_label,
    location_label,
    system_label,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceBusinessPartyOptionDescriptor,
    MaintenanceComponentOptionDescriptor,
    MaintenanceEmployeeOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_business_party_option,
    serialize_component_option,
    serialize_employee_option,
    serialize_location_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.modules.maintenance.api.desktop.work_orders.models import (
    MaintenanceSourceWorkRequestOptionDescriptor,
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderDesktopDto,
    MaintenanceWorkOrderStatusDescriptor,
    MaintenanceWorkOrderTypeDescriptor,
    MaintenanceWorkOrderUpdateCommand,
)
from src.core.modules.maintenance.api.desktop.work_orders.serializers import (
    serialize_source_work_request_option,
    serialize_work_order,
    source_work_request_label,
)
from src.core.modules.maintenance.api.desktop.work_requests.models import (
    MaintenancePriorityDescriptor,
)
from src.core.modules.maintenance.domain import (
    MaintenancePriority,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderType,
    MaintenanceWorkRequestStatus,
)
from src.core.platform.employee import EmployeeService
from src.core.platform.site import SiteService
from src.core.platform.party import PartyService, PartyType

_VENDOR_PARTY_TYPES = {
    PartyType.SUPPLIER,
    PartyType.VENDOR,
    PartyType.CONTRACTOR,
    PartyType.SERVICE_PROVIDER,
}
_SOURCE_REQUEST_STATUSES = (
    MaintenanceWorkRequestStatus.NEW,
    MaintenanceWorkRequestStatus.TRIAGED,
    MaintenanceWorkRequestStatus.APPROVED,
    MaintenanceWorkRequestStatus.DEFERRED,
)


class MaintenanceWorkOrdersDesktopApi:
    def __init__(
        self,
        *,
        work_order_service: MaintenanceWorkOrderService | None = None,
        work_request_service: MaintenanceWorkRequestService | None = None,
        site_service: SiteService | None = None,
        employee_service: EmployeeService | None = None,
        party_service: PartyService | None = None,
        location_service: MaintenanceLocationService | None = None,
        system_service: MaintenanceSystemService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        component_service: MaintenanceAssetComponentService | None = None,
    ) -> None:
        self._work_order_service = work_order_service
        self._work_request_service = work_request_service
        self._site_service = site_service
        self._employee_service = employee_service
        self._party_service = party_service
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

    def list_statuses(self) -> tuple[MaintenanceWorkOrderStatusDescriptor, ...]:
        return tuple(
            MaintenanceWorkOrderStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in MaintenanceWorkOrderStatus
        )

    def list_work_order_types(self) -> tuple[MaintenanceWorkOrderTypeDescriptor, ...]:
        return tuple(
            MaintenanceWorkOrderTypeDescriptor(
                value=work_order_type.value,
                label=format_enum_label(work_order_type.value),
            )
            for work_order_type in MaintenanceWorkOrderType
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

    def list_employee_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceEmployeeOptionDescriptor, ...]:
        if self._employee_service is None:
            return ()
        rows = sorted(
            (
                row
                for row in self._employee_service.list_employees(active_only=active_only)
                if site_id is None or getattr(row, "site_id", None) == site_id
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "full_name", "") or "").casefold(),
                str(getattr(row, "employee_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_employee_option(row) for row in rows)

    def list_vendor_parties(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[MaintenanceBusinessPartyOptionDescriptor, ...]:
        if self._party_service is None:
            return ()
        rows = sorted(
            (
                row
                for row in self._party_service.list_parties(active_only=active_only)
                if getattr(row, "party_type", None) in _VENDOR_PARTY_TYPES
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "party_name", "") or "").casefold(),
                str(getattr(row, "party_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_business_party_option(row) for row in rows)

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
            service.list_components(active_only=active_only, asset_id=asset_id),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "component_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_component_option(row) for row in rows)

    def list_source_work_request_options(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
    ) -> tuple[MaintenanceSourceWorkRequestOptionDescriptor, ...]:
        service = self._require_work_request_service()
        rows_by_id: dict[str, object] = {}
        for status in _SOURCE_REQUEST_STATUSES:
            for row in service.list_work_requests(
                site_id=site_id,
                asset_id=asset_id,
                component_id=component_id,
                system_id=system_id,
                location_id=location_id,
                status=status.value,
            ):
                rows_by_id[row.id] = row
        rows = sorted(
            rows_by_id.values(),
            key=lambda row: (
                getattr(getattr(row, "requested_at", None), "isoformat", lambda: "")(),
                str(getattr(row, "work_request_code", "") or "").casefold(),
            ),
            reverse=True,
        )
        return tuple(serialize_source_work_request_option(row) for row in rows)

    def list_work_orders(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        planner_user_id: str | None = None,
        supervisor_user_id: str | None = None,
        work_order_type: str | None = None,
        is_preventive: bool | None = None,
        is_emergency: bool | None = None,
    ) -> tuple[MaintenanceWorkOrderDesktopDto, ...]:
        service = self._require_work_order_service()
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = self._system_label_lookup(active_only=None)
        asset_lookup = self._asset_label_lookup(active_only=None)
        component_lookup = self._component_label_lookup(active_only=None)
        employee_lookup = self._employee_label_lookup(active_only=None)
        party_lookup = self._vendor_party_label_lookup(active_only=None)
        source_lookup = self._work_request_label_lookup()
        rows = sorted(
            service.list_work_orders(
                site_id=site_id,
                asset_id=asset_id,
                component_id=component_id,
                system_id=system_id,
                location_id=location_id,
                status=status,
                priority=priority,
                assigned_employee_id=assigned_employee_id,
                assigned_team_id=assigned_team_id,
                planner_user_id=planner_user_id,
                supervisor_user_id=supervisor_user_id,
                work_order_type=work_order_type,
                is_preventive=is_preventive,
                is_emergency=is_emergency,
            ),
            key=lambda row: (
                getattr(getattr(row, "created_at", None), "isoformat", lambda: "")(),
                str(getattr(row, "work_order_code", "") or "").casefold(),
            ),
            reverse=True,
        )
        return tuple(
            serialize_work_order(
                row,
                site_lookup=site_lookup,
                location_lookup=location_lookup,
                system_lookup=system_lookup,
                asset_lookup=asset_lookup,
                component_lookup=component_lookup,
                employee_lookup=employee_lookup,
                party_lookup=party_lookup,
                source_lookup=source_lookup,
            )
            for row in rows
        )

    def create_work_order(
        self,
        command: MaintenanceWorkOrderCreateCommand,
    ) -> MaintenanceWorkOrderDesktopDto:
        service = self._require_work_order_service()
        row = service.create_work_order(
            site_id=command.site_id,
            work_order_code=command.work_order_code,
            work_order_type=command.work_order_type,
            source_type=command.source_type,
            source_id=command.source_id,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            location_id=command.location_id,
            title=command.title,
            description=command.description,
            priority=command.priority,
            assigned_team_id=command.assigned_team_id,
            requires_shutdown=command.requires_shutdown,
            permit_required=command.permit_required,
            approval_required=command.approval_required,
            vendor_party_id=command.vendor_party_id,
            is_preventive=command.is_preventive,
            is_emergency=command.is_emergency,
            notes=command.notes,
        )
        return self._serialize_work_order_by_id(row.id)

    def update_work_order(
        self,
        command: MaintenanceWorkOrderUpdateCommand,
    ) -> MaintenanceWorkOrderDesktopDto:
        service = self._require_work_order_service()
        row = service.update_work_order(
            command.work_order_id,
            work_order_code=command.work_order_code,
            work_order_type=command.work_order_type,
            source_id=command.source_id,
            asset_id=command.asset_id,
            component_id=command.component_id,
            system_id=command.system_id,
            location_id=command.location_id,
            title=command.title,
            description=command.description,
            priority=command.priority,
            status=command.status,
            planner_user_id=command.planner_user_id,
            supervisor_user_id=command.supervisor_user_id,
            assigned_team_id=command.assigned_team_id,
            assigned_employee_id=command.assigned_employee_id,
            planned_start=parse_datetime_text(command.planned_start),
            planned_end=parse_datetime_text(command.planned_end),
            requires_shutdown=command.requires_shutdown,
            permit_required=command.permit_required,
            approval_required=command.approval_required,
            failure_code=command.failure_code,
            root_cause_code=command.root_cause_code,
            downtime_minutes=command.downtime_minutes,
            parts_cost=decimal_value(command.parts_cost),
            labor_cost=decimal_value(command.labor_cost),
            vendor_party_id=command.vendor_party_id,
            is_preventive=command.is_preventive,
            is_emergency=command.is_emergency,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_work_order_by_id(row.id)

    def _serialize_work_order_by_id(
        self,
        work_order_id: str,
    ) -> MaintenanceWorkOrderDesktopDto:
        row = self._require_work_order_service().get_work_order(work_order_id)
        return serialize_work_order(
            row,
            site_lookup=self._site_lookup(active_only=None),
            location_lookup=self._location_label_lookup(active_only=None),
            system_lookup=self._system_label_lookup(active_only=None),
            asset_lookup=self._asset_label_lookup(active_only=None),
            component_lookup=self._component_label_lookup(active_only=None),
            employee_lookup=self._employee_label_lookup(active_only=None),
            party_lookup=self._vendor_party_label_lookup(active_only=None),
            source_lookup=self._work_request_label_lookup(),
        )

    def _site_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {option.value: option.label for option in self.list_sites(active_only=active_only)}

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

    def _employee_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_employee_options(active_only=active_only)
        }

    def _vendor_party_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_vendor_parties(active_only=active_only)
        }

    def _work_request_label_lookup(self) -> dict[str, str]:
        service = self._require_work_request_service()
        rows_by_id: dict[str, str] = {}
        for status in MaintenanceWorkRequestStatus:
            for row in service.list_work_requests(status=status.value):
                rows_by_id[row.id] = source_work_request_label(row)
        return rows_by_id

    def _require_work_order_service(self) -> MaintenanceWorkOrderService:
        if self._work_order_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._work_order_service

    def _require_work_request_service(self) -> MaintenanceWorkRequestService:
        if self._work_request_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._work_request_service

    def _require_location_service(self) -> MaintenanceLocationService:
        if self._location_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._location_service

    def _require_system_service(self) -> MaintenanceSystemService:
        if self._system_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._system_service

    def _require_asset_service(self) -> MaintenanceAssetService:
        if self._asset_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._asset_service

    def _require_component_service(self) -> MaintenanceAssetComponentService:
        if self._component_service is None:
            raise RuntimeError("Maintenance work-orders desktop API is not connected.")
        return self._component_service


def build_maintenance_work_orders_desktop_api(
    *,
    work_order_service: MaintenanceWorkOrderService | None = None,
    work_request_service: MaintenanceWorkRequestService | None = None,
    site_service: SiteService | None = None,
    employee_service: EmployeeService | None = None,
    party_service: PartyService | None = None,
    location_service: MaintenanceLocationService | None = None,
    system_service: MaintenanceSystemService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    component_service: MaintenanceAssetComponentService | None = None,
) -> MaintenanceWorkOrdersDesktopApi:
    return MaintenanceWorkOrdersDesktopApi(
        work_order_service=work_order_service,
        work_request_service=work_request_service,
        site_service=site_service,
        employee_service=employee_service,
        party_service=party_service,
        location_service=location_service,
        system_service=system_service,
        asset_service=asset_service,
        component_service=component_service,
    )


__all__ = [
    "MaintenanceWorkOrdersDesktopApi",
    "build_maintenance_work_orders_desktop_api",
]
