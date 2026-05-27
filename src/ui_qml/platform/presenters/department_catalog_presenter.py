from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    DepartmentCreateCommand,
    DepartmentDto,
    DepartmentLocationReferenceDto,
    DepartmentUpdateCommand,
    PlatformDepartmentDesktopApi,
    PlatformSiteDesktopApi,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.ui_qml.platform.presenters.support import (
    bool_value,
    int_value,
    option_item,
    optional_string_value,
    preview_error_result,
    string_value,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformDepartmentCatalogPresenter:
    def __init__(
        self,
        *,
        department_api: PlatformDepartmentDesktopApi | None = None,
        site_api: PlatformSiteDesktopApi | None = None,
    ) -> None:
        self._department_api = department_api
        self._site_api = site_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._department_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle="Shared department records appear here once the platform department API is connected.",
                empty_state="Platform department API is not connected in this QML preview.",
            )

        context_result = self._department_api.get_context()
        departments_result = self._department_api.list_departments(active_only=None)
        site_lookup = self._site_lookup()
        location_lookup = self._location_lookup()
        if not departments_result.ok or departments_result.data is None:
            message = (
                departments_result.error.message
                if departments_result.error is not None
                else "Unable to load departments."
            )
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
            )

        context_label = (
            context_result.data.display_name
            if context_result.ok and context_result.data is not None
            else "Context unavailable"
        )
        return PlatformWorkspaceActionListViewModel(
            title="Departments",
            subtitle=f"Shared department records for {context_label}.",
            empty_state="No departments are available yet.",
            items=tuple(
                self._serialize_department(
                    row,
                    site_lookup=site_lookup,
                    location_lookup=location_lookup,
                )
                for row in departments_result.data
            ),
        )

    def build_site_options(self) -> tuple[dict[str, str], ...]:
        if self._site_api is None:
            return ()
        result = self._site_api.list_sites(active_only=True)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=row.name,
                value=row.id,
                supporting_text=f"{row.site_code} | {row.city or '-'}",
            )
            for row in result.data
        )

    def build_location_options(self) -> tuple[dict[str, str], ...]:
        if self._department_api is None:
            return ()
        result = self._department_api.list_location_references(active_only=True)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=row.name,
                value=row.id,
                supporting_text=f"{row.location_code} | Site {row.site_id}",
            )
            for row in result.data
        )

    def build_parent_options(self) -> tuple[dict[str, str], ...]:
        if self._department_api is None:
            return ()
        result = self._department_api.list_departments(active_only=None)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=row.name,
                value=row.id,
                supporting_text=row.department_code,
            )
            for row in result.data
        )

    def create_department(self, payload: dict[str, Any]) -> DesktopApiResult[DepartmentDto]:
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.create_department(
            DepartmentCreateCommand(
                department_code=string_value(payload, "departmentCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                site_id=optional_string_value(payload, "siteId"),
                default_location_id=optional_string_value(payload, "defaultLocationId"),
                parent_department_id=optional_string_value(payload, "parentDepartmentId"),
                department_type=string_value(payload, "departmentType"),
                cost_center_code=string_value(payload, "costCenterCode"),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
            )
        )

    def update_department(self, payload: dict[str, Any]) -> DesktopApiResult[DepartmentDto]:
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.update_department(
            DepartmentUpdateCommand(
                department_id=string_value(payload, "departmentId"),
                department_code=string_value(payload, "departmentCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                site_id=optional_string_value(payload, "siteId"),
                default_location_id=optional_string_value(payload, "defaultLocationId"),
                parent_department_id=optional_string_value(payload, "parentDepartmentId"),
                department_type=string_value(payload, "departmentType"),
                cost_center_code=string_value(payload, "costCenterCode"),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def toggle_department_active(
        self,
        *,
        department_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[DepartmentDto]:
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.update_department(
            DepartmentUpdateCommand(
                department_id=department_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    def _site_lookup(self) -> dict[str, str]:
        if self._site_api is None:
            return {}
        result = self._site_api.list_sites(active_only=None)
        if not result.ok or result.data is None:
            return {}
        return {
            row.id: row.name
            for row in result.data
        }

    def _location_lookup(self) -> dict[str, str]:
        if self._department_api is None:
            return {}
        result = self._department_api.list_location_references(active_only=True)
        if not result.ok or result.data is None:
            return {}
        return {
            row.id: f"{row.location_code} - {row.name}"
            for row in result.data
        }

    @staticmethod
    def _serialize_department(
        row: DepartmentDto,
        *,
        site_lookup: dict[str, str],
        location_lookup: dict[str, str],
    ) -> PlatformWorkspaceActionItemViewModel:
        site_label = site_lookup.get(row.site_id or "", "No site")
        location_label = location_lookup.get(row.default_location_id or "", "No default location")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.department_code} | {row.department_type or 'Department'}",
            supporting_text=f"Site: {site_label} | Location: {location_label}",
            meta_text=f"Cost center: {row.cost_center_code or '-'}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "departmentId": row.id,
                "departmentCode": row.department_code,
                "name": row.name,
                "description": row.description,
                "siteId": row.site_id or "",
                "defaultLocationId": row.default_location_id or "",
                "parentDepartmentId": row.parent_department_id or "",
                "departmentType": row.department_type,
                "costCenterCode": row.cost_center_code,
                "notes": row.notes,
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformDepartmentCatalogPresenter"]
