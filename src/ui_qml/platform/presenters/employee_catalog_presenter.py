from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    EmployeeCreateCommand,
    EmployeeDto,
    EmployeeUpdateCommand,
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
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


class PlatformEmployeeCatalogPresenter:
    def __init__(
        self,
        *,
        employee_api: PlatformEmployeeDesktopApi | None = None,
        site_api: PlatformSiteDesktopApi | None = None,
        department_api: PlatformDepartmentDesktopApi | None = None,
    ) -> None:
        self._employee_api = employee_api
        self._site_api = site_api
        self._department_api = department_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._employee_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle="Workforce records appear here once the platform employee API is connected.",
                empty_state="Platform employee API is not connected in this QML preview.",
            )

        result = self._employee_api.list_employees(active_only=None)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load employees."
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Employees",
            subtitle="Internal employee directory for staffing and cross-module reference data.",
            empty_state="No employees are available yet.",
            items=tuple(self._serialize_employee(row) for row in result.data),
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

    def build_department_options(self) -> tuple[dict[str, str], ...]:
        if self._department_api is None:
            return ()
        result = self._department_api.list_departments(active_only=True)
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

    def create_employee(self, payload: dict[str, Any]) -> DesktopApiResult[EmployeeDto]:
        if self._employee_api is None:
            return preview_error_result("Platform employee API is not connected in this QML preview.")
        return self._employee_api.create_employee(
            EmployeeCreateCommand(
                employee_code=string_value(payload, "employeeCode"),
                full_name=string_value(payload, "fullName"),
                department_id=optional_string_value(payload, "departmentId"),
                department=string_value(payload, "departmentName"),
                site_id=optional_string_value(payload, "siteId"),
                site_name=string_value(payload, "siteName"),
                title=string_value(payload, "title"),
                employment_type=string_value(payload, "employmentType", default="FULL_TIME"),
                email=optional_string_value(payload, "email"),
                phone=optional_string_value(payload, "phone"),
                is_active=bool_value(payload, "isActive", default=True),
            )
        )

    def update_employee(self, payload: dict[str, Any]) -> DesktopApiResult[EmployeeDto]:
        if self._employee_api is None:
            return preview_error_result("Platform employee API is not connected in this QML preview.")
        return self._employee_api.update_employee(
            EmployeeUpdateCommand(
                employee_id=string_value(payload, "employeeId"),
                employee_code=string_value(payload, "employeeCode"),
                full_name=string_value(payload, "fullName"),
                department_id=optional_string_value(payload, "departmentId"),
                department=string_value(payload, "departmentName"),
                site_id=optional_string_value(payload, "siteId"),
                site_name=string_value(payload, "siteName"),
                title=string_value(payload, "title"),
                employment_type=string_value(payload, "employmentType", default="FULL_TIME"),
                email=optional_string_value(payload, "email"),
                phone=optional_string_value(payload, "phone"),
                is_active=bool_value(payload, "isActive", default=True),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def toggle_employee_active(
        self,
        *,
        employee_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[EmployeeDto]:
        if self._employee_api is None:
            return preview_error_result("Platform employee API is not connected in this QML preview.")
        return self._employee_api.update_employee(
            EmployeeUpdateCommand(
                employee_id=employee_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    @staticmethod
    def _serialize_employee(row: EmployeeDto) -> PlatformWorkspaceActionItemViewModel:
        contact_label = row.email or row.phone or "No contact details"
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.full_name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.employee_code} | {row.title or 'No title'}",
            supporting_text=f"{row.department or 'No department'} | {row.site_name or 'No site'}",
            meta_text=f"{row.employment_type.replace('_', ' ').title()} | {contact_label}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "employeeId": row.id,
                "employeeCode": row.employee_code,
                "fullName": row.full_name,
                "departmentId": row.department_id or "",
                "departmentName": row.department,
                "siteId": row.site_id or "",
                "siteName": row.site_name,
                "title": row.title,
                "employmentType": row.employment_type,
                "email": row.email or "",
                "phone": row.phone or "",
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformEmployeeCatalogPresenter"]
