from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceCreateCommand,
    ResourceUpdateCommand,
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCatalogMetricViewModel,
    ResourceCatalogOverviewViewModel,
    ResourceCatalogWorkspaceViewModel,
    ResourceDetailFieldViewModel,
    ResourceDetailViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceRecordViewModel,
    ResourceSelectorOptionViewModel,
)


class ProjectResourcesWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementResourcesDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_resources_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        active_filter: str = "all",
        category_filter: str = "all",
        selected_resource_id: str | None = None,
    ) -> ResourceCatalogWorkspaceViewModel:
        all_resources = self._desktop_api.list_resources()
        worker_type_options = tuple(
            ResourceSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_worker_types()
        )
        category_options = (
            ResourceSelectorOptionViewModel(value="all", label="All categories"),
            *(
                ResourceSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_categories()
            ),
        )
        employee_options = tuple(
            ResourceEmployeeOptionViewModel(
                value=option.value,
                label=option.label,
                name=option.name,
                title=option.title,
                contact=option.contact,
                context=option.context,
                is_active=option.is_active,
            )
            for option in self._desktop_api.list_employees()
        )
        normalized_search = (search_text or "").strip()
        normalized_active_filter = self._normalize_active_filter(active_filter)
        normalized_category_filter = self._normalize_category_filter(
            category_filter,
            category_options,
        )
        filtered_resources = tuple(
            resource
            for resource in all_resources
            if self._matches_active(resource, normalized_active_filter)
            and self._matches_category(resource, normalized_category_filter)
            and self._matches_search(resource, normalized_search)
        )
        resolved_selected_resource_id = self._resolve_selected_resource_id(
            selected_resource_id,
            filtered_resources,
        )
        selected_resource = next(
            (
                resource
                for resource in filtered_resources
                if resource.id == resolved_selected_resource_id
            ),
            None,
        )
        return ResourceCatalogWorkspaceViewModel(
            overview=self._build_overview(
                all_resources=all_resources,
                filtered_resources=filtered_resources,
            ),
            worker_type_options=worker_type_options,
            category_options=category_options,
            employee_options=employee_options,
            selected_active_filter=normalized_active_filter,
            selected_category_filter=normalized_category_filter,
            search_text=normalized_search,
            resources=tuple(
                self._to_resource_record_view_model(resource)
                for resource in filtered_resources
            ),
            selected_resource_id=resolved_selected_resource_id,
            selected_resource_detail=self._build_detail_view_model(selected_resource),
            empty_state=self._build_empty_state(
                all_resources=all_resources,
                filtered_resources=filtered_resources,
                search_text=normalized_search,
                active_filter=normalized_active_filter,
                category_filter=normalized_category_filter,
            ),
        )

    def create_resource(self, payload: dict[str, Any]) -> None:
        command = ResourceCreateCommand(
            name=self._optional_text(payload, "name") or "",
            role=self._optional_text(payload, "role") or "",
            hourly_rate=self._optional_float(payload, "hourlyRate", "Hourly rate must be a valid number.", default=0.0),
            is_active=self._optional_bool(payload, "isActive", default=True),
            cost_type=self._optional_text(payload, "costType") or CostType.LABOR.value,
            currency_code=self._optional_text(payload, "currency"),
            capacity_percent=self._optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
            address=self._optional_text(payload, "address") or "",
            contact=self._optional_text(payload, "contact") or "",
            worker_type=self._optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
            employee_id=self._optional_text(payload, "employeeId"),
        )
        self._desktop_api.create_resource(command)

    def update_resource(self, payload: dict[str, Any]) -> None:
        command = ResourceUpdateCommand(
            resource_id=self._require_text(
                payload,
                "resourceId",
                "Resource ID is required for updates.",
            ),
            name=self._optional_text(payload, "name") or "",
            role=self._optional_text(payload, "role") or "",
            hourly_rate=self._optional_float(payload, "hourlyRate", "Hourly rate must be a valid number.", default=0.0),
            is_active=self._optional_bool(payload, "isActive", default=True),
            cost_type=self._optional_text(payload, "costType") or CostType.LABOR.value,
            currency_code=self._optional_text(payload, "currency"),
            capacity_percent=self._optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
            address=self._optional_text(payload, "address") or "",
            contact=self._optional_text(payload, "contact") or "",
            worker_type=self._optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
            employee_id=self._optional_text(payload, "employeeId"),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_resource(command)

    def toggle_resource_active(
        self,
        resource_id: str,
        expected_version: int | None = None,
    ) -> None:
        normalized_resource_id = (resource_id or "").strip()
        if not normalized_resource_id:
            raise ValueError("Resource ID is required to update availability.")
        self._desktop_api.toggle_resource_active(
            normalized_resource_id,
            expected_version=expected_version,
        )

    def delete_resource(self, resource_id: str) -> None:
        normalized_resource_id = (resource_id or "").strip()
        if not normalized_resource_id:
            raise ValueError("Resource ID is required to delete a resource.")
        self._desktop_api.delete_resource(normalized_resource_id)

    @staticmethod
    def _build_overview(
        *,
        all_resources,
        filtered_resources,
    ) -> ResourceCatalogOverviewViewModel:
        total_capacity = sum(float(resource.capacity_percent or 0.0) for resource in all_resources)
        average_capacity = total_capacity / len(all_resources) if all_resources else 0.0
        employee_count = sum(1 for resource in all_resources if resource.worker_type == WorkerType.EMPLOYEE.value)
        external_count = sum(1 for resource in all_resources if resource.worker_type == WorkerType.EXTERNAL.value)
        active_count = sum(1 for resource in all_resources if resource.is_active)
        return ResourceCatalogOverviewViewModel(
            title="Resources",
            subtitle="Resource capacity, staffing type, and pool availability workflows.",
            metrics=(
                ResourceCatalogMetricViewModel(
                    label="Total resources",
                    value=str(len(all_resources)),
                    supporting_text=f"Showing {len(filtered_resources)} with the current filters.",
                ),
                ResourceCatalogMetricViewModel(
                    label="Active",
                    value=str(active_count),
                    supporting_text="Resources currently available for assignment.",
                ),
                ResourceCatalogMetricViewModel(
                    label="Employees",
                    value=str(employee_count),
                    supporting_text="Resources linked to the shared employee directory.",
                ),
                ResourceCatalogMetricViewModel(
                    label="External",
                    value=str(external_count),
                    supporting_text="Vendor or contract resources managed locally in PM.",
                ),
                ResourceCatalogMetricViewModel(
                    label="Avg capacity",
                    value=f"{average_capacity:.1f}%",
                    supporting_text="Average capacity across the current PM resource pool.",
                ),
            ),
        )

    def _build_detail_view_model(self, resource) -> ResourceDetailViewModel:
        if resource is None:
            return ResourceDetailViewModel(
                title="No resource selected",
                empty_state="Select a resource from the catalog to review details or edit its setup.",
            )
        state = self._build_resource_state(resource)
        subtitle_parts = [state["role"], state["employeeContext"]]
        subtitle_values = [part for part in subtitle_parts if part and part != "-"]
        if not subtitle_values:
            subtitle_values = [state["workerTypeLabel"]]
        description = (
            "Employee-linked resource ready for cross-workspace staffing."
            if state["workerType"] == WorkerType.EMPLOYEE.value
            else "External resource record ready for project assignment and cost planning."
        )
        return ResourceDetailViewModel(
            id=resource.id,
            title=resource.name,
            status_label=resource.active_label,
            subtitle=" | ".join(subtitle_values),
            description=description,
            fields=(
                ResourceDetailFieldViewModel(
                    label="Worker type",
                    value=state["workerTypeLabel"],
                    supporting_text=state["employeeContext"],
                ),
                ResourceDetailFieldViewModel(
                    label="Category",
                    value=state["costTypeLabel"],
                ),
                ResourceDetailFieldViewModel(
                    label="Hourly rate",
                    value=state["hourlyRateLabel"],
                    supporting_text=state["currency"] or "Uses the PM default currency when left blank.",
                ),
                ResourceDetailFieldViewModel(
                    label="Capacity",
                    value=state["capacityLabel"],
                ),
                ResourceDetailFieldViewModel(
                    label="Contact",
                    value=state["contact"] or "No contact recorded",
                ),
                ResourceDetailFieldViewModel(
                    label="Address",
                    value=state["address"] or "No address recorded",
                ),
                ResourceDetailFieldViewModel(
                    label="Version",
                    value=str(state["version"]),
                ),
            ),
            state=state,
        )

    def _to_resource_record_view_model(self, resource) -> ResourceRecordViewModel:
        state = self._build_resource_state(resource)
        subtitle_parts = [state["role"], state["workerTypeLabel"]]
        subtitle_values = [part for part in subtitle_parts if part]
        meta_parts = []
        if state["employeeContext"] and state["employeeContext"] != "-":
            meta_parts.append(state["employeeContext"])
        if state["contact"]:
            meta_parts.append(state["contact"])
        return ResourceRecordViewModel(
            id=resource.id,
            title=resource.name,
            status_label=resource.active_label,
            subtitle=" | ".join(subtitle_values) or "No role assigned",
            supporting_text=(
                f"{state['costTypeLabel']} | {state['hourlyRateLabel']} | Capacity {state['capacityLabel']}"
            ),
            meta_text=" | ".join(meta_parts),
            state=state,
        )

    @staticmethod
    def _build_resource_state(resource) -> dict[str, object]:
        return {
            "resourceId": resource.id,
            "name": resource.name,
            "role": resource.role or "",
            "workerType": resource.worker_type,
            "workerTypeLabel": resource.worker_type_label,
            "costType": resource.cost_type,
            "costTypeLabel": resource.cost_type_label,
            "hourlyRate": f"{float(resource.hourly_rate or 0.0):.2f}",
            "hourlyRateLabel": resource.hourly_rate_label,
            "currency": resource.currency_code or "",
            "capacityPercent": f"{float(resource.capacity_percent or 0.0):.1f}",
            "capacityLabel": resource.capacity_label,
            "address": resource.address or "",
            "contact": resource.contact or "",
            "employeeId": resource.employee_id or "",
            "employeeContext": resource.employee_context or "-",
            "isActive": resource.is_active,
            "activeLabel": resource.active_label,
            "version": resource.version,
        }

    @staticmethod
    def _matches_search(resource, search_text: str) -> bool:
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            resource.name or "",
            resource.role or "",
            resource.worker_type_label or "",
            resource.cost_type_label or "",
            resource.employee_context or "",
            resource.contact or "",
            resource.address or "",
            resource.currency_code or "",
        )
        return any(normalized_search in value.casefold() for value in haystacks)

    @staticmethod
    def _matches_active(resource, active_filter: str) -> bool:
        if active_filter == "all":
            return True
        if active_filter == "active":
            return bool(resource.is_active)
        if active_filter == "inactive":
            return not bool(resource.is_active)
        return True

    @staticmethod
    def _matches_category(resource, category_filter: str) -> bool:
        if category_filter == "all":
            return True
        return resource.cost_type == category_filter

    @staticmethod
    def _resolve_selected_resource_id(selected_resource_id: str | None, filtered_resources) -> str:
        normalized_id = (selected_resource_id or "").strip()
        if normalized_id and any(resource.id == normalized_id for resource in filtered_resources):
            return normalized_id
        if filtered_resources:
            return filtered_resources[0].id
        return ""

    @staticmethod
    def _normalize_active_filter(active_filter: str) -> str:
        normalized_value = (active_filter or "all").strip().lower()
        if normalized_value in {"all", "active", "inactive"}:
            return normalized_value
        return "all"

    @staticmethod
    def _normalize_category_filter(category_filter: str, category_options) -> str:
        normalized_value = (category_filter or "all").strip().upper()
        available_values = {option.value.upper(): option.value for option in category_options}
        return available_values.get(normalized_value, "all")

    @staticmethod
    def _build_empty_state(
        *,
        all_resources,
        filtered_resources,
        search_text: str,
        active_filter: str,
        category_filter: str,
    ) -> str:
        if filtered_resources:
            return ""
        if not all_resources:
            return "No resources are available yet. Create the first PM resource to start planning capacity."
        if search_text or active_filter != "all" or category_filter != "all":
            return "No resources match the current filters."
        return "No resources are available yet."

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
    def _optional_float(
        payload: dict[str, Any],
        key: str,
        message: str,
        *,
        default: float,
    ) -> float:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return float(default)
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
        value = payload.get(key)
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["ProjectResourcesWorkspacePresenter"]
