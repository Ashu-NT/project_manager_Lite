from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.master_data.department.department import PlatformDepartmentDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.master_data.employee.models.employee import (
    EmployeeCreateCommand,
    EmployeeDto,
    EmployeeUpdateCommand,
)
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
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

# Employee lifecycle is a plain boolean (is_active) -- a 2-state
# Active/Inactive model, structurally different from Organization's 3-state
# ACTIVE/INACTIVE/ARCHIVED enum. Do not conflate the two tone maps.
_EMPLOYEE_STATUS_TONE = {True: "success", False: "neutral"}


def _employee_status_label(is_active: bool) -> dict[str, str]:
    return {"label": "Active" if is_active else "Inactive", "tone": _EMPLOYEE_STATUS_TONE[is_active]}


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

    def build_catalog_for_department(self, department_id: str) -> PlatformWorkspaceActionListViewModel:
        if self._employee_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle="Workforce records appear here once the platform employee API is connected.",
                empty_state="Platform employee API is not connected in this QML preview.",
            )

        result = self._employee_api.list_employees(department_id=department_id)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load employees."
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Employees",
            subtitle="Employees aligned to this department through the shared employee master.",
            empty_state="This department does not currently have employees assigned.",
            items=tuple(self._serialize_employee(row) for row in result.data),
        )

    def build_catalog_for_site(self, site_id: str) -> PlatformWorkspaceActionListViewModel:
        if self._employee_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle="Workforce records appear here once the platform employee API is connected.",
                empty_state="Platform employee API is not connected in this QML preview.",
            )

        result = self._employee_api.list_employees(site_id=site_id)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load employees."
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Employees",
            subtitle="Employees aligned to this site through the shared employee master.",
            empty_state="This site does not currently have employees assigned.",
            items=tuple(self._serialize_employee(row) for row in result.data),
        )

    def build_catalog_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Tenant-scoped (not active-organization-scoped) paginated
        Employees page for Organization Detail's Employees tab -- works
        regardless of which organization is currently active in the
        caller's session."""
        if self._employee_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle="Employees appear here once the platform employee API is connected.",
                empty_state="Platform employee API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )

        active_only: bool | None
        if status == "active":
            active_only = True
        elif status == "inactive":
            active_only = False
        else:
            active_only = None

        result = self._employee_api.list_employees_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load employees."
            return PlatformWorkspaceActionListViewModel(
                title="Employees",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        employee_page = result.data
        return PlatformWorkspaceActionListViewModel(
            title="Employees",
            subtitle="Workforce records for this organization.",
            empty_state="No employees yet. Add the first employee for this organization.",
            no_results_state="No employees match your current filters.",
            items=tuple(self._serialize_employee(row) for row in employee_page.items),
            paginated=True,
            page=employee_page.page,
            page_size=employee_page.page_size,
            total_count=employee_page.total,
            filtered_total=employee_page.filtered_total,
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

    def suggest_code(self, payload: dict[str, Any]) -> str:
        """Suggest a unique employee code (EMP-<NAME>-0001 / EMP-<YEAR>-0001)."""
        from src.core.platform.common.code_generation import CodeGenerator

        existing: set[str] = set()
        if self._employee_api is not None:
            result = self._employee_api.list_employees(active_only=None)
            if result.ok and result.data is not None:
                existing = {str(getattr(row, "employee_code", "") or "").upper() for row in result.data}
        name = string_value(payload, "fullName")
        return CodeGenerator().generate(
            "employee",
            exists=lambda code: code.upper() in existing,
            name=name or None,
            use_year=not bool(name),
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
            status_label=_employee_status_label(row.is_active),
            subtitle=f"{row.employee_code} | {row.title or 'No title'}",
            supporting_text=f"{row.department or 'No department'} | {row.site_name or 'No site'}",
            meta_text=f"{row.employment_type.replace('_', ' ').title()} | {contact_label}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "employeeId": row.id,
                "organizationId": row.organization_id or "",
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
