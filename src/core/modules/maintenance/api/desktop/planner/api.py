from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenanceReliabilityService,
    MaintenanceSensorExceptionService,
    MaintenanceSystemService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.api.desktop.planner.models import (
    MAINTENANCE_PLANNER_ALL_REQUESTS,
    MAINTENANCE_PLANNER_ALL_WORK_ORDERS,
    MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS,
    MAINTENANCE_PLANNER_OPEN_REQUESTS,
    MaintenancePlannerMetricDescriptor,
    MaintenancePlannerOverviewDescriptor,
    MaintenancePlannerQueueDescriptor,
    MaintenancePlannerSnapshotDescriptor,
)
from src.core.modules.maintenance.api.desktop.planner.serializers import (
    request_search_blob,
    serialize_material_risk_row,
    serialize_preventive_row,
    serialize_recurring_row,
    serialize_request_row,
    serialize_work_order_row,
    work_order_search_blob,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.modules.maintenance.domain import MaintenanceWorkOrderStatus, MaintenanceWorkRequestStatus
from src.core.platform.org import SiteService

_OPEN_REQUEST_STATUSES = {
    MaintenanceWorkRequestStatus.NEW.value,
    MaintenanceWorkRequestStatus.TRIAGED.value,
    MaintenanceWorkRequestStatus.APPROVED.value,
    MaintenanceWorkRequestStatus.DEFERRED.value,
}
_CLOSED_WORK_ORDER_STATUSES = {
    MaintenanceWorkOrderStatus.COMPLETED.value,
    MaintenanceWorkOrderStatus.VERIFIED.value,
    MaintenanceWorkOrderStatus.CLOSED.value,
    MaintenanceWorkOrderStatus.CANCELLED.value,
}
_MATERIAL_RISK_STATUSES = {
    "PLANNED",
    "SHORTAGE_IDENTIFIED",
    "REQUISITIONED",
    "PARTIALLY_ISSUED",
    "NON_STOCK",
}


class MaintenancePlannerDesktopApi:
    def __init__(
        self,
        *,
        site_service: SiteService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        system_service: MaintenanceSystemService | None = None,
        work_request_service: MaintenanceWorkRequestService | None = None,
        work_order_service: MaintenanceWorkOrderService | None = None,
        material_requirement_service: MaintenanceWorkOrderMaterialRequirementService | None = None,
        preventive_plan_service: MaintenancePreventivePlanService | None = None,
        preventive_generation_service: MaintenancePreventiveGenerationService | None = None,
        reliability_service: MaintenanceReliabilityService | None = None,
        sensor_exception_service: MaintenanceSensorExceptionService | None = None,
    ) -> None:
        self._site_service = site_service
        self._asset_service = asset_service
        self._system_service = system_service
        self._work_request_service = work_request_service
        self._work_order_service = work_order_service
        self._material_requirement_service = material_requirement_service
        self._preventive_plan_service = preventive_plan_service
        self._preventive_generation_service = preventive_generation_service
        self._reliability_service = reliability_service
        self._sensor_exception_service = sensor_exception_service

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
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> tuple[MaintenanceAssetOptionDescriptor, ...]:
        if self._asset_service is None:
            return ()
        rows = sorted(
            self._asset_service.list_assets(
                active_only=active_only,
                site_id=site_id,
            ),
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
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> tuple[MaintenanceSystemOptionDescriptor, ...]:
        if self._system_service is None:
            return ()
        rows = sorted(
            self._system_service.list_systems(
                active_only=active_only,
                site_id=site_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "system_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_system_option(row) for row in rows)

    def list_request_queue_options(self) -> tuple[MaintenancePlannerQueueDescriptor, ...]:
        return (
            MaintenancePlannerQueueDescriptor(
                value=MAINTENANCE_PLANNER_OPEN_REQUESTS,
                label="Open requests",
            ),
            MaintenancePlannerQueueDescriptor(
                value=MAINTENANCE_PLANNER_ALL_REQUESTS,
                label="All request statuses",
            ),
            *(
                MaintenancePlannerQueueDescriptor(
                    value=status.value,
                    label=status.value.replace("_", " ").title(),
                )
                for status in (
                    MaintenanceWorkRequestStatus.NEW,
                    MaintenanceWorkRequestStatus.TRIAGED,
                    MaintenanceWorkRequestStatus.APPROVED,
                    MaintenanceWorkRequestStatus.REJECTED,
                    MaintenanceWorkRequestStatus.CONVERTED,
                    MaintenanceWorkRequestStatus.DEFERRED,
                )
            ),
        )

    def list_work_order_queue_options(self) -> tuple[MaintenancePlannerQueueDescriptor, ...]:
        return (
            MaintenancePlannerQueueDescriptor(
                value=MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS,
                label="Backlog orders",
            ),
            MaintenancePlannerQueueDescriptor(
                value=MAINTENANCE_PLANNER_ALL_WORK_ORDERS,
                label="All work orders",
            ),
            *(
                MaintenancePlannerQueueDescriptor(
                    value=status.value,
                    label=status.value.replace("_", " ").title(),
                )
                for status in (
                    MaintenanceWorkOrderStatus.PLANNED,
                    MaintenanceWorkOrderStatus.WAITING_PARTS,
                    MaintenanceWorkOrderStatus.WAITING_APPROVAL,
                    MaintenanceWorkOrderStatus.WAITING_SHUTDOWN,
                    MaintenanceWorkOrderStatus.SCHEDULED,
                    MaintenanceWorkOrderStatus.RELEASED,
                    MaintenanceWorkOrderStatus.IN_PROGRESS,
                    MaintenanceWorkOrderStatus.PAUSED,
                    MaintenanceWorkOrderStatus.COMPLETED,
                    MaintenanceWorkOrderStatus.VERIFIED,
                    MaintenanceWorkOrderStatus.CLOSED,
                    MaintenanceWorkOrderStatus.CANCELLED,
                )
            ),
        )

    def build_empty_overview(self) -> MaintenancePlannerOverviewDescriptor:
        return MaintenancePlannerOverviewDescriptor(
            title="Planner",
            subtitle=(
                "Coordinate intake, backlog, preventive readiness, material planning, "
                "and recurring failure priorities from one maintenance planning surface."
            ),
            metrics=(
                MaintenancePlannerMetricDescriptor("Open Requests", "0", "Intake still needing planner attention"),
                MaintenancePlannerMetricDescriptor("Backlog Orders", "0", "Orders still in planning or execution queues"),
                MaintenancePlannerMetricDescriptor("Preventive Review", "0", "Due, due-soon, and blocked preventive plans"),
                MaintenancePlannerMetricDescriptor("Material Risks", "0", "Requirements not yet fully ready"),
                MaintenancePlannerMetricDescriptor("Recurring Patterns", "0", "Failure patterns to review while planning"),
            ),
        )

    def build_snapshot(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        request_queue: str = MAINTENANCE_PLANNER_OPEN_REQUESTS,
        work_order_queue: str = MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS,
        search_text: str = "",
    ) -> MaintenancePlannerSnapshotDescriptor:
        site_options = self.list_sites(active_only=None)
        selected_site_id = self._resolve_option_value(site_id, site_options)
        asset_options = self.list_asset_options(active_only=None, site_id=selected_site_id or None)
        selected_asset_id = self._resolve_option_value(asset_id, asset_options)
        system_options = self.list_system_options(active_only=None, site_id=selected_site_id or None)
        selected_system_id = self._resolve_option_value(system_id, system_options)
        request_queue_options = self.list_request_queue_options()
        selected_request_queue = self._resolve_queue_value(request_queue, request_queue_options)
        work_order_queue_options = self.list_work_order_queue_options()
        selected_work_order_queue = self._resolve_queue_value(work_order_queue, work_order_queue_options)
        normalized_search = str(search_text or "").strip().lower()

        if self._work_request_service is None or self._work_order_service is None:
            return MaintenancePlannerSnapshotDescriptor(
                overview=self.build_empty_overview(),
                site_options=site_options,
                selected_site_id=selected_site_id,
                asset_options=asset_options,
                selected_asset_id=selected_asset_id,
                system_options=system_options,
                selected_system_id=selected_system_id,
                request_queue_options=request_queue_options,
                selected_request_queue=selected_request_queue,
                work_order_queue_options=work_order_queue_options,
                selected_work_order_queue=selected_work_order_queue,
                search_text=search_text,
                empty_state="Maintenance planner desktop API is not fully connected.",
            )

        request_rows = list(
            self._work_request_service.list_work_requests(
                site_id=selected_site_id or None,
                asset_id=selected_asset_id or None,
                system_id=selected_system_id or None,
            )
        )
        work_order_rows = list(
            self._work_order_service.list_work_orders(
                site_id=selected_site_id or None,
                asset_id=selected_asset_id or None,
                system_id=selected_system_id or None,
            )
        )
        material_requirement_rows = (
            list(self._material_requirement_service.list_requirements())
            if self._material_requirement_service is not None
            else []
        )
        preventive_plans = (
            list(
                self._preventive_plan_service.search_preventive_plans(
                    search_text=search_text,
                    active_only=None,
                    site_id=selected_site_id or None,
                    asset_id=selected_asset_id or None,
                    system_id=selected_system_id or None,
                )
            )
            if self._preventive_plan_service is not None
            else []
        )
        preventive_candidates = (
            list(
                self._preventive_generation_service.list_due_candidates(
                    site_id=selected_site_id or None,
                )
            )
            if self._preventive_generation_service is not None
            else []
        )
        recurring_rows = (
            list(
                self._reliability_service.list_recurring_failure_patterns(
                    site_id=selected_site_id or None,
                    asset_id=selected_asset_id or None,
                    system_id=selected_system_id or None,
                    min_occurrences=2,
                    limit=10,
                )
            )
            if self._reliability_service is not None
            else []
        )
        exception_rows = (
            list(self._sensor_exception_service.list_exceptions(status="OPEN"))
            if self._sensor_exception_service is not None
            else []
        )

        if selected_request_queue == MAINTENANCE_PLANNER_OPEN_REQUESTS:
            request_rows = [
                row
                for row in request_rows
                if getattr(getattr(row, "status", None), "value", "") in _OPEN_REQUEST_STATUSES
            ]
        elif selected_request_queue != MAINTENANCE_PLANNER_ALL_REQUESTS:
            request_rows = [
                row
                for row in request_rows
                if getattr(getattr(row, "status", None), "value", "") == selected_request_queue
            ]
        if selected_work_order_queue == MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS:
            work_order_rows = [
                row
                for row in work_order_rows
                if getattr(getattr(row, "status", None), "value", "") not in _CLOSED_WORK_ORDER_STATUSES
            ]
        elif selected_work_order_queue != MAINTENANCE_PLANNER_ALL_WORK_ORDERS:
            work_order_rows = [
                row
                for row in work_order_rows
                if getattr(getattr(row, "status", None), "value", "") == selected_work_order_queue
            ]
        if normalized_search:
            request_rows = [row for row in request_rows if normalized_search in request_search_blob(row)]
            work_order_rows = [row for row in work_order_rows if normalized_search in work_order_search_blob(row)]

        site_lookup = {option.value: option.label for option in site_options}
        asset_lookup = {option.value: option.label for option in asset_options}
        system_lookup = {option.value: option.label for option in system_options}
        work_order_descriptors = tuple(serialize_work_order_row(row) for row in work_order_rows)
        work_order_label_lookup = {
            row.id: descriptor.work_order_label
            for row, descriptor in zip(work_order_rows, work_order_descriptors)
        }
        work_order_ids = set(work_order_label_lookup)
        preventive_candidate_lookup = {row.plan_id: row for row in preventive_candidates}
        material_rows = tuple(
            serialize_material_risk_row(
                row,
                work_order_label=work_order_label_lookup.get(row.work_order_id, row.work_order_id),
            )
            for row in material_requirement_rows
            if row.work_order_id in work_order_ids
            and getattr(getattr(row, "procurement_status", None), "value", "") in _MATERIAL_RISK_STATUSES
        )
        preventive_rows = tuple(
            sorted(
                (
                    serialize_preventive_row(
                        row,
                        candidate=preventive_candidate_lookup.get(row.id),
                        site_lookup=site_lookup,
                        asset_lookup=asset_lookup,
                        system_lookup=system_lookup,
                    )
                    for row in preventive_plans
                ),
                key=self._preventive_sort_key,
            )
        )

        exception_count_by_anchor: dict[str, int] = {}
        for row in exception_rows:
            anchor_id = getattr(row, "sensor_id", None) or getattr(row, "integration_source_id", None) or ""
            if anchor_id:
                exception_count_by_anchor[str(anchor_id)] = exception_count_by_anchor.get(str(anchor_id), 0) + 1

        overview = MaintenancePlannerOverviewDescriptor(
            title="Planner",
            subtitle=(
                "Coordinate intake, backlog, preventive readiness, material planning, "
                "and recurring failure priorities from one maintenance planning surface."
            ),
            metrics=(
                MaintenancePlannerMetricDescriptor(
                    "Open Requests",
                    str(len(request_rows)),
                    "Intake still needing planner attention",
                ),
                MaintenancePlannerMetricDescriptor(
                    "Backlog Orders",
                    str(len(work_order_rows)),
                    "Orders still in planning or execution queues",
                ),
                MaintenancePlannerMetricDescriptor(
                    "Preventive Review",
                    str(len(preventive_rows)),
                    "Due, due-soon, and blocked preventive plans",
                ),
                MaintenancePlannerMetricDescriptor(
                    "Material Risks",
                    str(len(material_rows)),
                    "Requirements not yet fully ready",
                ),
                MaintenancePlannerMetricDescriptor(
                    "Recurring Patterns",
                    str(len(recurring_rows)),
                    "Failure patterns to review while planning",
                ),
            ),
        )

        return MaintenancePlannerSnapshotDescriptor(
            overview=overview,
            site_options=site_options,
            selected_site_id=selected_site_id,
            asset_options=asset_options,
            selected_asset_id=selected_asset_id,
            system_options=system_options,
            selected_system_id=selected_system_id,
            request_queue_options=request_queue_options,
            selected_request_queue=selected_request_queue,
            work_order_queue_options=work_order_queue_options,
            selected_work_order_queue=selected_work_order_queue,
            search_text=search_text,
            request_rows=tuple(
                serialize_request_row(
                    row,
                    site_lookup=site_lookup,
                    asset_lookup=asset_lookup,
                    system_lookup=system_lookup,
                )
                for row in request_rows
            ),
            work_order_rows=work_order_descriptors,
            material_rows=material_rows,
            preventive_rows=preventive_rows,
            recurring_rows=tuple(
                serialize_recurring_row(
                    row,
                    exception_count_by_anchor=exception_count_by_anchor,
                )
                for row in recurring_rows
            ),
            empty_state="" if any((request_rows, work_order_rows, material_rows, preventive_rows, recurring_rows)) else "No planner items match the current filters.",
        )

    @staticmethod
    def _resolve_option_value(value: str | None, options) -> str:
        normalized = str(value or "").strip()
        if normalized and any(option.value == normalized for option in options):
            return normalized
        return ""

    @staticmethod
    def _resolve_queue_value(value: str | None, options) -> str:
        normalized = str(value or "").strip()
        if normalized and any(option.value == normalized for option in options):
            return normalized
        return options[0].value if options else normalized

    @staticmethod
    def _preventive_sort_key(row) -> tuple[int, str, str, str]:
        if row.due_state == "DUE":
            priority = 0
        elif row.due_state == "BLOCKED":
            priority = 1
        elif row.is_due_soon:
            priority = 2
        elif row.due_state == "NOT_DUE":
            priority = 3
        else:
            priority = 4
        return (priority, row.next_due_label, row.plan_code, row.plan_id)


def build_maintenance_planner_desktop_api(
    *,
    site_service: SiteService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    system_service: MaintenanceSystemService | None = None,
    work_request_service: MaintenanceWorkRequestService | None = None,
    work_order_service: MaintenanceWorkOrderService | None = None,
    material_requirement_service: MaintenanceWorkOrderMaterialRequirementService | None = None,
    preventive_plan_service: MaintenancePreventivePlanService | None = None,
    preventive_generation_service: MaintenancePreventiveGenerationService | None = None,
    reliability_service: MaintenanceReliabilityService | None = None,
    sensor_exception_service: MaintenanceSensorExceptionService | None = None,
) -> MaintenancePlannerDesktopApi:
    return MaintenancePlannerDesktopApi(
        site_service=site_service,
        asset_service=asset_service,
        system_service=system_service,
        work_request_service=work_request_service,
        work_order_service=work_order_service,
        material_requirement_service=material_requirement_service,
        preventive_plan_service=preventive_plan_service,
        preventive_generation_service=preventive_generation_service,
        reliability_service=reliability_service,
        sensor_exception_service=sensor_exception_service,
    )


__all__ = [
    "MaintenancePlannerDesktopApi",
    "build_maintenance_planner_desktop_api",
]
