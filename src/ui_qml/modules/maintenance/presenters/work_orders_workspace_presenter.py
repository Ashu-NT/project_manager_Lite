from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
    MaintenanceWorkOrdersDesktopApi,
    build_maintenance_work_orders_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrderDetailFieldViewModel,
    MaintenanceWorkOrderDetailViewModel,
    MaintenanceWorkOrderMetricViewModel,
    MaintenanceWorkOrderOptionViewModel,
    MaintenanceWorkOrderOverviewViewModel,
    MaintenanceWorkOrderRecordViewModel,
    MaintenanceWorkOrdersWorkspaceViewModel,
)


def _option(value: str, label: str) -> MaintenanceWorkOrderOptionViewModel:
    return MaintenanceWorkOrderOptionViewModel(value=value, label=label)


_SOURCE_TYPE_OPTIONS = (
    _option("MANUAL", "Manual"),
    _option("WORK_REQUEST", "Work Request"),
)


class MaintenanceWorkOrdersWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceWorkOrdersDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_work_orders_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        status_filter: str = "all",
        priority_filter: str = "all",
        work_order_type_filter: str = "all",
        asset_filter: str = "all",
        selected_work_order_id: str | None = None,
    ) -> MaintenanceWorkOrdersWorkspaceViewModel:
        site_options = (
            _option("all", "All sites"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_sites(active_only=None)
            ),
        )
        status_options = (
            _option("all", "All statuses"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_statuses()
            ),
        )
        priority_options = (
            _option("all", "All priorities"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_priorities()
            ),
        )
        work_order_type_options = (
            _option("all", "All work-order types"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_work_order_types()
            ),
        )

        normalized_site_filter = self._normalize_filter(site_filter, site_options)
        asset_options = (
            _option("all", "All assets"),
            *(
                _option(option.value, option.label)
                for option in self._desktop_api.list_asset_options(
                    active_only=None,
                    site_id=None if normalized_site_filter == "all" else normalized_site_filter,
                )
            ),
        )
        normalized_status_filter = self._normalize_filter(status_filter, status_options)
        normalized_priority_filter = self._normalize_filter(
            priority_filter,
            priority_options,
        )
        normalized_work_order_type_filter = self._normalize_filter(
            work_order_type_filter,
            work_order_type_options,
        )
        normalized_asset_filter = self._normalize_filter(asset_filter, asset_options)
        normalized_search = (search_text or "").strip()

        all_rows = self._desktop_api.list_work_orders()
        filtered_rows = self._desktop_api.list_work_orders(
            site_id=None if normalized_site_filter == "all" else normalized_site_filter,
            status=None if normalized_status_filter == "all" else normalized_status_filter,
            priority=None
            if normalized_priority_filter == "all"
            else normalized_priority_filter,
            work_order_type=None
            if normalized_work_order_type_filter == "all"
            else normalized_work_order_type_filter,
            asset_id=None if normalized_asset_filter == "all" else normalized_asset_filter,
        )
        if normalized_search:
            filtered_rows = tuple(
                row
                for row in filtered_rows
                if self._matches_search(
                    normalized_search,
                    row.work_order_code,
                    row.title,
                    row.description,
                    row.work_order_type,
                    row.work_order_type_label,
                    row.source_type,
                    row.source_type_label,
                    row.source_label,
                    row.asset_label,
                    row.component_label,
                    row.system_label,
                    row.location_label,
                    row.status,
                    row.status_label,
                    row.priority,
                    row.priority_label,
                    row.vendor_party_label,
                    row.assigned_employee_label,
                    row.failure_code,
                    row.root_cause_code,
                    row.notes,
                )
            )

        resolved_selected_id = self._resolve_selected_id(
            selected_work_order_id,
            filtered_rows,
        )
        selected_row = next(
            (row for row in filtered_rows if row.id == resolved_selected_id),
            None,
        )

        site_id_for_forms = (
            None if normalized_site_filter == "all" else normalized_site_filter
        )
        return MaintenanceWorkOrdersWorkspaceViewModel(
            overview=self._build_overview(all_rows=all_rows, filtered_rows=filtered_rows),
            site_options=site_options,
            status_options=status_options,
            priority_options=priority_options,
            work_order_type_options=work_order_type_options,
            asset_options=asset_options,
            selected_site_filter=normalized_site_filter,
            selected_status_filter=normalized_status_filter,
            selected_priority_filter=normalized_priority_filter,
            selected_work_order_type_filter=normalized_work_order_type_filter,
            selected_asset_filter=normalized_asset_filter,
            search_text=normalized_search,
            work_orders=tuple(self._to_record_view_model(row) for row in filtered_rows),
            selected_work_order_id=resolved_selected_id,
            selected_work_order_detail=self._build_detail(selected_row),
            form_site_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_sites(active_only=None)
            ),
            form_location_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_location_options(
                    active_only=None,
                    site_id=site_id_for_forms,
                )
            ),
            form_system_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_system_options(
                    active_only=None,
                    site_id=site_id_for_forms,
                )
            ),
            form_asset_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_asset_options(
                    active_only=None,
                    site_id=site_id_for_forms,
                )
            ),
            form_component_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_component_options(active_only=None)
            ),
            form_source_type_options=_SOURCE_TYPE_OPTIONS,
            form_source_work_request_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_source_work_request_options(
                    site_id=site_id_for_forms
                )
            ),
            form_work_order_type_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_work_order_types()
            ),
            form_priority_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_priorities()
            ),
            form_status_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_statuses()
            ),
            form_employee_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_employee_options(
                    active_only=None,
                    site_id=site_id_for_forms,
                )
            ),
            form_vendor_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_vendor_parties(active_only=None)
            ),
            empty_state=self._build_empty_state(
                all_rows=all_rows,
                filtered_rows=filtered_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                status_filter=normalized_status_filter,
                priority_filter=normalized_priority_filter,
                work_order_type_filter=normalized_work_order_type_filter,
                asset_filter=normalized_asset_filter,
            ),
        )

    def create_work_order(self, payload: dict[str, Any]) -> None:
        source_type = self._require_text(
            payload,
            "sourceType",
            "Choose a source type before saving.",
        )
        source_id = self._optional_text(payload, "sourceId")
        title = self._optional_text(payload, "title") or ""
        if source_type == "WORK_REQUEST" and not source_id:
            raise ValueError(
                "Choose a source work request before saving a converted work order."
            )
        if source_type != "WORK_REQUEST" and not title:
            raise ValueError("Title is required.")
        command = MaintenanceWorkOrderCreateCommand(
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            work_order_code=self._require_text(
                payload,
                "workOrderCode",
                "Work order code is required.",
            ),
            work_order_type=self._require_text(
                payload,
                "workOrderType",
                "Choose a work-order type before saving.",
            ),
            source_type=source_type,
            source_id=source_id,
            asset_id=self._optional_text(payload, "assetId"),
            component_id=self._optional_text(payload, "componentId"),
            system_id=self._optional_text(payload, "systemId"),
            location_id=self._optional_text(payload, "locationId"),
            title=title,
            description=self._optional_text(payload, "description") or "",
            priority=self._require_text(payload, "priority", "Choose a priority."),
            vendor_party_id=self._optional_text(payload, "vendorPartyId"),
            requires_shutdown=self._bool_value(payload, "requiresShutdown"),
            permit_required=self._bool_value(payload, "permitRequired"),
            approval_required=self._bool_value(payload, "approvalRequired"),
            is_preventive=self._bool_value(payload, "isPreventive"),
            is_emergency=self._bool_value(payload, "isEmergency"),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_work_order(command)

    def update_work_order(self, payload: dict[str, Any]) -> None:
        title = self._require_text(payload, "title", "Title is required.")
        command = MaintenanceWorkOrderUpdateCommand(
            work_order_id=self._require_text(
                payload,
                "workOrderId",
                "Work order ID is required before saving.",
            ),
            work_order_code=self._require_text(
                payload,
                "workOrderCode",
                "Work order code is required.",
            ),
            work_order_type=self._require_text(
                payload,
                "workOrderType",
                "Choose a work-order type before saving.",
            ),
            source_id=self._optional_text(payload, "sourceId"),
            asset_id=self._optional_text(payload, "assetId"),
            component_id=self._optional_text(payload, "componentId"),
            system_id=self._optional_text(payload, "systemId"),
            location_id=self._optional_text(payload, "locationId"),
            title=title,
            description=self._optional_text(payload, "description") or "",
            priority=self._require_text(payload, "priority", "Choose a priority."),
            vendor_party_id=self._optional_text(payload, "vendorPartyId"),
            requires_shutdown=self._bool_value(payload, "requiresShutdown"),
            permit_required=self._bool_value(payload, "permitRequired"),
            approval_required=self._bool_value(payload, "approvalRequired"),
            is_preventive=self._bool_value(payload, "isPreventive"),
            is_emergency=self._bool_value(payload, "isEmergency"),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_work_order(command)

    def set_work_order_status(
        self,
        work_order_id: str,
        *,
        status: str,
        expected_version: int,
    ) -> None:
        if not (work_order_id or "").strip():
            raise ValueError("Work order ID is required before updating status.")
        if not (status or "").strip():
            raise ValueError("Choose a status before saving.")
        self._desktop_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=work_order_id.strip(),
                status=status.strip(),
                expected_version=expected_version,
            )
        )

    @staticmethod
    def _build_overview(*, all_rows, filtered_rows) -> MaintenanceWorkOrderOverviewViewModel:
        draft_count = sum(1 for row in all_rows if row.status == "DRAFT")
        planned_count = sum(1 for row in all_rows if row.status == "PLANNED")
        active_count = sum(1 for row in all_rows if row.status == "IN_PROGRESS")
        return MaintenanceWorkOrderOverviewViewModel(
            title="Work Orders",
            subtitle="Execution planning, assignment readiness, and lifecycle control now render through the maintenance desktop API.",
            metrics=(
                MaintenanceWorkOrderMetricViewModel(
                    label="Orders",
                    value=str(len(all_rows)),
                    supporting_text=f"Showing {len(filtered_rows)} work orders with the current filters.",
                ),
                MaintenanceWorkOrderMetricViewModel(
                    label="Draft",
                    value=str(draft_count),
                    supporting_text="New execution records still waiting for planning detail.",
                ),
                MaintenanceWorkOrderMetricViewModel(
                    label="Planned",
                    value=str(planned_count),
                    supporting_text="Planned work that is ready for scheduling and release.",
                ),
                MaintenanceWorkOrderMetricViewModel(
                    label="Active",
                    value=str(active_count),
                    supporting_text="Orders already released into execution or currently in progress.",
                ),
            ),
        )

    @staticmethod
    def _to_record_view_model(row) -> MaintenanceWorkOrderRecordViewModel:
        plan_window = " | ".join(
            value
            for value in (row.planned_start or "", row.planned_end or "")
            if value
        )
        return MaintenanceWorkOrderRecordViewModel(
            id=row.id,
            title=row.work_order_code or row.title,
            status_label=row.status_label,
            subtitle=row.title,
            supporting_text=(
                f"{row.priority_label} | {row.work_order_type_label} | {row.asset_label}"
            ),
            meta_text=plan_window or f"Assigned: {row.assigned_employee_label}",
            state={
                "workOrderId": row.id,
                "siteId": row.site_id,
                "workOrderCode": row.work_order_code,
                "workOrderType": row.work_order_type,
                "sourceType": row.source_type,
                "sourceId": row.source_id or "",
                "sourceLabel": row.source_label,
                "assetId": row.asset_id or "",
                "componentId": row.component_id or "",
                "systemId": row.system_id or "",
                "locationId": row.location_id or "",
                "title": row.title,
                "description": row.description,
                "priority": row.priority,
                "status": row.status,
                "assignedEmployeeId": row.assigned_employee_id or "",
                "vendorPartyId": row.vendor_party_id or "",
                "plannedStart": row.planned_start,
                "plannedEnd": row.planned_end,
                "requiresShutdown": row.requires_shutdown,
                "permitRequired": row.permit_required,
                "approvalRequired": row.approval_required,
                "isPreventive": row.is_preventive,
                "isEmergency": row.is_emergency,
                "failureCode": row.failure_code,
                "rootCauseCode": row.root_cause_code,
                "downtimeMinutes": row.downtime_minutes if row.downtime_minutes is not None else "",
                "partsCost": row.parts_cost if row.parts_cost is not None else "",
                "laborCost": row.labor_cost if row.labor_cost is not None else "",
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    @staticmethod
    def _build_detail(row) -> MaintenanceWorkOrderDetailViewModel:
        if row is None:
            return MaintenanceWorkOrderDetailViewModel(
                title="No work order selected",
                empty_state="Select a work order to inspect its execution scope, planning status, and update actions.",
            )
        return MaintenanceWorkOrderDetailViewModel(
            id=row.id,
            title=f"{row.work_order_code or '-'} - {row.title}",
            status_label=row.status_label,
            subtitle=f"{row.priority_label} | {row.site_label}",
            description=row.description or "No execution description provided.",
            fields=(
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Type / Source",
                    value=f"{row.work_order_type_label} | {row.source_type_label}",
                    supporting_text=row.source_label,
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Anchor",
                    value=f"{row.asset_label} | {row.component_label}",
                    supporting_text=f"{row.system_label} | {row.location_label}",
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Assignment",
                    value=row.assigned_employee_label or "-",
                    supporting_text=f"Vendor: {row.vendor_party_label or '-'}",
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Plan window",
                    value=row.planned_start or "-",
                    supporting_text=f"End: {row.planned_end or '-'}",
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Execution window",
                    value=row.actual_start or "-",
                    supporting_text=f"End: {row.actual_end or '-'}",
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Flags",
                    value=(
                        f"Shutdown {MaintenanceWorkOrdersWorkspacePresenter._yes_no(row.requires_shutdown)} | "
                        f"Permit {MaintenanceWorkOrdersWorkspacePresenter._yes_no(row.permit_required)} | "
                        f"Approval {MaintenanceWorkOrdersWorkspacePresenter._yes_no(row.approval_required)}"
                    ),
                    supporting_text=(
                        f"Preventive {MaintenanceWorkOrdersWorkspacePresenter._yes_no(row.is_preventive)} | "
                        f"Emergency {MaintenanceWorkOrdersWorkspacePresenter._yes_no(row.is_emergency)}"
                    ),
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Failure / Cost",
                    value=f"{row.failure_code or '-'} | {row.root_cause_code or '-'}",
                    supporting_text=(
                        f"Labor {MaintenanceWorkOrdersWorkspacePresenter._money_text(row.labor_cost)} | "
                        f"Parts {MaintenanceWorkOrdersWorkspacePresenter._money_text(row.parts_cost)} | "
                        f"Downtime {row.downtime_minutes if row.downtime_minutes is not None else '-'} min"
                    ),
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceWorkOrderDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state={
                "workOrderId": row.id,
                "siteId": row.site_id,
                "workOrderCode": row.work_order_code,
                "workOrderType": row.work_order_type,
                "sourceType": row.source_type,
                "sourceId": row.source_id or "",
                "sourceLabel": row.source_label,
                "assetId": row.asset_id or "",
                "componentId": row.component_id or "",
                "systemId": row.system_id or "",
                "locationId": row.location_id or "",
                "title": row.title,
                "description": row.description,
                "priority": row.priority,
                "status": row.status,
                "assignedEmployeeId": row.assigned_employee_id or "",
                "vendorPartyId": row.vendor_party_id or "",
                "plannedStart": row.planned_start,
                "plannedEnd": row.planned_end,
                "requiresShutdown": row.requires_shutdown,
                "permitRequired": row.permit_required,
                "approvalRequired": row.approval_required,
                "isPreventive": row.is_preventive,
                "isEmergency": row.is_emergency,
                "failureCode": row.failure_code,
                "rootCauseCode": row.root_cause_code,
                "downtimeMinutes": row.downtime_minutes if row.downtime_minutes is not None else "",
                "partsCost": row.parts_cost if row.parts_cost is not None else "",
                "laborCost": row.labor_cost if row.labor_cost is not None else "",
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    @staticmethod
    def _matches_search(search_text: str, *values: str) -> bool:
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"

    @staticmethod
    def _build_empty_state(
        *,
        all_rows,
        filtered_rows,
        search_text: str,
        site_filter: str,
        status_filter: str,
        priority_filter: str,
        work_order_type_filter: str,
        asset_filter: str,
    ) -> str:
        if filtered_rows:
            return ""
        if not all_rows:
            return "No work orders are available yet. Create a work order to start the execution flow."
        if (
            search_text
            or site_filter != "all"
            or status_filter != "all"
            or priority_filter != "all"
            or work_order_type_filter != "all"
            or asset_filter != "all"
        ):
            return "No work orders match the current filters."
        return "No work orders are available yet."

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, message: str) -> int:
        value = payload.get(key, None)
        if value in (None, ""):
            raise ValueError(message)
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _bool_value(payload: dict[str, Any], key: str) -> bool:
        return bool(payload.get(key, False))

    @staticmethod
    def _yes_no(value: bool) -> str:
        return "Yes" if value else "No"

    @staticmethod
    def _money_text(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}"


__all__ = ["MaintenanceWorkOrdersWorkspacePresenter"]
