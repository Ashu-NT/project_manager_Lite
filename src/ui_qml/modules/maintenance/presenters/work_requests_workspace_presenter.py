from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkRequestUpdateCommand,
    MaintenanceWorkRequestsDesktopApi,
    build_maintenance_work_requests_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestDetailFieldViewModel,
    MaintenanceWorkRequestDetailViewModel,
    MaintenanceWorkRequestMetricViewModel,
    MaintenanceWorkRequestOptionViewModel,
    MaintenanceWorkRequestOverviewViewModel,
    MaintenanceWorkRequestRecordViewModel,
    MaintenanceWorkRequestsWorkspaceViewModel,
)


def _option(value: str, label: str) -> MaintenanceWorkRequestOptionViewModel:
    return MaintenanceWorkRequestOptionViewModel(value=value, label=label)


class MaintenanceWorkRequestsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceWorkRequestsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_work_requests_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        status_filter: str = "all",
        priority_filter: str = "all",
        asset_filter: str = "all",
        selected_work_request_id: str | None = None,
    ) -> MaintenanceWorkRequestsWorkspaceViewModel:
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
        normalized_asset_filter = self._normalize_filter(asset_filter, asset_options)
        normalized_search = (search_text or "").strip()

        all_rows = self._desktop_api.list_work_requests()
        filtered_rows = self._desktop_api.list_work_requests(
            site_id=None if normalized_site_filter == "all" else normalized_site_filter,
            status=None
            if normalized_status_filter == "all"
            else normalized_status_filter,
            priority=None
            if normalized_priority_filter == "all"
            else normalized_priority_filter,
            asset_id=None if normalized_asset_filter == "all" else normalized_asset_filter,
        )
        if normalized_search:
            filtered_rows = tuple(
                row
                for row in filtered_rows
                if self._matches_search(
                    normalized_search,
                    row.work_request_code,
                    row.title,
                    row.description,
                    row.asset_label,
                    row.component_label,
                    row.system_label,
                    row.location_label,
                    row.status,
                    row.status_label,
                    row.priority,
                    row.priority_label,
                    row.failure_symptom_code,
                    row.requested_by_name,
                    row.notes,
                )
            )

        resolved_selected_id = self._resolve_selected_id(
            selected_work_request_id,
            filtered_rows,
        )
        selected_row = next(
            (row for row in filtered_rows if row.id == resolved_selected_id),
            None,
        )

        return MaintenanceWorkRequestsWorkspaceViewModel(
            overview=self._build_overview(all_rows=all_rows, filtered_rows=filtered_rows),
            site_options=site_options,
            status_options=status_options,
            priority_options=priority_options,
            asset_options=asset_options,
            selected_site_filter=normalized_site_filter,
            selected_status_filter=normalized_status_filter,
            selected_priority_filter=normalized_priority_filter,
            selected_asset_filter=normalized_asset_filter,
            search_text=normalized_search,
            work_requests=tuple(self._to_record_view_model(row) for row in filtered_rows),
            selected_work_request_id=resolved_selected_id,
            selected_work_request_detail=self._build_detail(selected_row),
            form_site_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_sites(active_only=None)
            ),
            form_location_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_location_options(active_only=None)
            ),
            form_system_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_system_options(active_only=None)
            ),
            form_asset_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_asset_options(active_only=None)
            ),
            form_component_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_component_options(active_only=None)
            ),
            form_source_type_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_source_types()
            ),
            form_priority_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_priorities()
            ),
            form_status_options=tuple(
                _option(option.value, option.label)
                for option in self._desktop_api.list_statuses()
            ),
            empty_state=self._build_empty_state(
                all_rows=all_rows,
                filtered_rows=filtered_rows,
                search_text=normalized_search,
                site_filter=normalized_site_filter,
                status_filter=normalized_status_filter,
                priority_filter=normalized_priority_filter,
                asset_filter=normalized_asset_filter,
            ),
        )

    def create_work_request(self, payload: dict[str, Any]) -> None:
        command = MaintenanceWorkRequestCreateCommand(
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            work_request_code=self._optional_text(payload, "workRequestCode") or "",
            source_type=self._require_text(
                payload,
                "sourceType",
                "Choose a source type before saving.",
            ),
            source_id=self._optional_text(payload, "sourceId"),
            request_type=self._require_text(
                payload,
                "requestType",
                "Request type is required.",
            ),
            asset_id=self._optional_text(payload, "assetId"),
            component_id=self._optional_text(payload, "componentId"),
            system_id=self._optional_text(payload, "systemId"),
            location_id=self._optional_text(payload, "locationId"),
            title=self._require_text(payload, "title", "Title is required."),
            description=self._optional_text(payload, "description") or "",
            priority=self._require_text(payload, "priority", "Choose a priority."),
            failure_symptom_code=self._optional_text(payload, "failureSymptomCode") or "",
            safety_risk_level=self._optional_text(payload, "safetyRiskLevel") or "",
            production_impact_level=self._optional_text(payload, "productionImpactLevel")
            or "",
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_work_request(command)

    def update_work_request(self, payload: dict[str, Any]) -> None:
        command = MaintenanceWorkRequestUpdateCommand(
            work_request_id=self._require_text(
                payload,
                "workRequestId",
                "Work request ID is required before saving.",
            ),
            work_request_code=self._optional_text(payload, "workRequestCode"),
            request_type=self._optional_text(payload, "requestType"),
            asset_id=self._optional_text(payload, "assetId"),
            component_id=self._optional_text(payload, "componentId"),
            system_id=self._optional_text(payload, "systemId"),
            location_id=self._optional_text(payload, "locationId"),
            title=self._optional_text(payload, "title"),
            description=self._optional_text(payload, "description"),
            priority=self._optional_text(payload, "priority"),
            status=self._optional_text(payload, "status"),
            failure_symptom_code=self._optional_text(payload, "failureSymptomCode"),
            safety_risk_level=self._optional_text(payload, "safetyRiskLevel"),
            production_impact_level=self._optional_text(payload, "productionImpactLevel"),
            notes=self._optional_text(payload, "notes"),
            expected_version=self._require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
        self._desktop_api.update_work_request(command)

    def set_work_request_status(
        self,
        work_request_id: str,
        *,
        status: str,
        expected_version: int,
    ) -> None:
        if not (work_request_id or "").strip():
            raise ValueError("Work request ID is required before updating status.")
        if not (status or "").strip():
            raise ValueError("Choose a status before saving.")
        self._desktop_api.update_work_request(
            MaintenanceWorkRequestUpdateCommand(
                work_request_id=work_request_id.strip(),
                status=status.strip(),
                expected_version=expected_version,
            )
        )

    @staticmethod
    def _build_overview(*, all_rows, filtered_rows) -> MaintenanceWorkRequestOverviewViewModel:
        new_count = sum(1 for row in all_rows if row.status == "NEW")
        triaged_count = sum(1 for row in all_rows if row.status == "TRIAGED")
        approved_count = sum(1 for row in all_rows if row.status == "APPROVED")
        return MaintenanceWorkRequestOverviewViewModel(
            title="Work Requests",
            subtitle="Request intake, triage progression, and conversion-ready backlog now render through the maintenance desktop API.",
            metrics=(
                MaintenanceWorkRequestMetricViewModel(
                    label="Requests",
                    value=str(len(all_rows)),
                    supporting_text=f"Showing {len(filtered_rows)} requests with the current filters.",
                ),
                MaintenanceWorkRequestMetricViewModel(
                    label="New",
                    value=str(new_count),
                    supporting_text="Fresh intake still waiting for first triage.",
                ),
                MaintenanceWorkRequestMetricViewModel(
                    label="Triaged",
                    value=str(triaged_count),
                    supporting_text="Requests already assessed and ready for the next decision.",
                ),
                MaintenanceWorkRequestMetricViewModel(
                    label="Approved",
                    value=str(approved_count),
                    supporting_text="Requests already approved for conversion or execution planning.",
                ),
            ),
        )

    @staticmethod
    def _to_record_view_model(row) -> MaintenanceWorkRequestRecordViewModel:
        return MaintenanceWorkRequestRecordViewModel(
            id=row.id,
            title=row.work_request_code or row.title,
            status_label=row.status_label,
            subtitle=row.title,
            supporting_text=(
                f"{row.priority_label} | {row.asset_label} | {row.location_label}"
            ),
            meta_text=(
                f"Requested {row.requested_at or '-'} by {row.requested_by_name or '-'}"
            ),
            state={
                "workRequestId": row.id,
                "workRequestCode": row.work_request_code,
                "siteId": row.site_id,
                "assetId": row.asset_id or "",
                "assetLabel": row.asset_label,
                "componentId": row.component_id or "",
                "systemId": row.system_id or "",
                "locationId": row.location_id or "",
                "locationLabel": row.location_label,
                "sourceType": row.source_type,
                "sourceId": row.source_id or "",
                "requestType": row.request_type,
                "title": row.title,
                "description": row.description,
                "priority": row.priority,
                "priorityLabel": row.priority_label,
                "status": row.status,
                "requestedAt": row.requested_at or "",
                "requestedByName": row.requested_by_name or "",
                "failureSymptomCode": row.failure_symptom_code,
                "safetyRiskLevel": row.safety_risk_level,
                "productionImpactLevel": row.production_impact_level,
                "notes": row.notes,
                "expectedVersion": row.version,
                "canPrimaryAction": True,
                "canSecondaryAction": True,
            },
        )

    @staticmethod
    def _build_detail(row) -> MaintenanceWorkRequestDetailViewModel:
        if row is None:
            return MaintenanceWorkRequestDetailViewModel(
                title="No work request selected",
                empty_state="Select a work request to inspect its intake context, triage state, and update actions.",
            )
        return MaintenanceWorkRequestDetailViewModel(
            id=row.id,
            title=f"{row.work_request_code or '-'} - {row.title}",
            status_label=row.status_label,
            subtitle=f"{row.priority_label} | {row.site_label}",
            description=row.description or "No request description provided.",
            fields=(
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Source",
                    value=f"{row.source_type_label} | {row.source_id or '-'}",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Request type",
                    value=row.request_type or "-",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Anchor",
                    value=f"{row.asset_label} | {row.component_label}",
                    supporting_text=f"{row.system_label} | {row.location_label}",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Requested",
                    value=row.requested_at or "-",
                    supporting_text=f"By {row.requested_by_name or '-'}",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Triaged",
                    value=row.triaged_at or "-",
                    supporting_text=f"By {row.triaged_by_label or '-'}",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Failure / Risk",
                    value=row.failure_symptom_code or "-",
                    supporting_text=(
                        f"Safety {row.safety_risk_level or '-'} | "
                        f"Production {row.production_impact_level or '-'}"
                    ),
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Notes",
                    value=row.notes or "-",
                ),
                MaintenanceWorkRequestDetailFieldViewModel(
                    label="Version",
                    value=str(row.version),
                ),
            ),
            state={
                "workRequestId": row.id,
                "workRequestCode": row.work_request_code,
                "siteId": row.site_id,
                "assetId": row.asset_id or "",
                "componentId": row.component_id or "",
                "systemId": row.system_id or "",
                "locationId": row.location_id or "",
                "sourceType": row.source_type,
                "sourceId": row.source_id or "",
                "requestType": row.request_type,
                "title": row.title,
                "description": row.description,
                "priority": row.priority,
                "status": row.status,
                "failureSymptomCode": row.failure_symptom_code,
                "safetyRiskLevel": row.safety_risk_level,
                "productionImpactLevel": row.production_impact_level,
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
        asset_filter: str,
    ) -> str:
        if filtered_rows:
            return ""
        if not all_rows:
            return "No work requests are available yet. Create a request to start the intake and triage flow."
        if (
            search_text
            or site_filter != "all"
            or status_filter != "all"
            or priority_filter != "all"
            or asset_filter != "all"
        ):
            return "No work requests match the current filters."
        return "No work requests are available yet."

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


__all__ = ["MaintenanceWorkRequestsWorkspacePresenter"]
