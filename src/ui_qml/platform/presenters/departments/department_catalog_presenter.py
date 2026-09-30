from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.master_data.department.department import (
    PlatformDepartmentDesktopApi,
)
from src.core.platform.api.desktop.master_data.department.models.department import (
    DepartmentCreateCommand,
    DepartmentDto,
    DepartmentUpdateCommand,
)
from src.core.platform.api.desktop.master_data.employee.employee import (
    PlatformEmployeeDesktopApi,
)
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
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

# Department lifecycle is a plain boolean (is_active) -- a 2-state
# Active/Inactive model, structurally different from Organization's 3-state
# ACTIVE/INACTIVE/ARCHIVED enum. Do not conflate the two tone maps.
_DEPARTMENT_STATUS_TONE = {True: "success", False: "neutral"}


def _department_status_label(is_active: bool) -> dict[str, str]:
    return {"label": "Active" if is_active else "Inactive", "tone": _DEPARTMENT_STATUS_TONE[is_active]}


class PlatformDepartmentCatalogPresenter:
    def __init__(
        self,
        *,
        department_api: PlatformDepartmentDesktopApi | None = None,
        site_api: PlatformSiteDesktopApi | None = None,
        employee_api: PlatformEmployeeDesktopApi | None = None,
    ) -> None:
        self._department_api = department_api
        self._site_api = site_api
        self._employee_api = employee_api

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
        employee_lookup = self._employee_lookup()
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
                    employee_lookup=employee_lookup,
                )
                for row in departments_result.data
            ),
        )

    def build_catalog_for_site(self, site_id: str) -> PlatformWorkspaceActionListViewModel:
        """Explicit site_id-scoped Departments read for Site Detail's own
        Departments tab -- a real backend filter (DepartmentService.
        list_departments(site_id=...)), not a client-side filter of the
        shared, session-active-organization-only catalog."""
        if self._department_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle="Departments appear here once the platform department API is connected.",
                empty_state="Platform department API is not connected in this QML preview.",
            )

        result = self._department_api.list_departments(active_only=None, site_id=site_id)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load departments."
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
            )

        site_lookup = self._site_lookup()
        employee_lookup = self._employee_lookup()
        return PlatformWorkspaceActionListViewModel(
            title="Departments",
            subtitle="Departments aligned to this site through the shared department master.",
            empty_state="This site does not currently have departments assigned.",
            items=tuple(
                self._serialize_department(row, site_lookup=site_lookup, employee_lookup=employee_lookup)
                for row in result.data
            ),
        )

    def build_catalog_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
        site_id: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Server-side paginated Departments page for the primary Platform >
        Departments destination, scoped to the caller's currently active
        organization -- the ambient-context counterpart to
        build_catalog_page_for_organization below (Organization Detail's
        explicit-organization_id variant). Optional site_id narrows to a
        single Site, the same real backend filter build_catalog_page_for_site
        uses for Site Detail's own Departments tab -- never a client-side
        filter of an already-fetched page."""
        if self._department_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle="Departments appear here once the platform department API is connected.",
                empty_state="Platform department API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )
        context_result = self._department_api.get_context()
        if not context_result.ok or context_result.data is None:
            message = context_result.error.message if context_result.error is not None else "Unable to load departments."
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        organization_id = context_result.data.id
        active_only: bool | None
        if status == "active":
            active_only = True
        elif status == "inactive":
            active_only = False
        else:
            active_only = None

        result = self._department_api.list_departments_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
            site_id=site_id or None,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load departments."
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        department_page = result.data
        site_lookup = self._site_lookup_for_organization(organization_id)
        department_lookup = self._department_lookup_for_organization(organization_id)
        employee_lookup = self._employee_lookup_for_organization(organization_id)
        return PlatformWorkspaceActionListViewModel(
            title="Departments",
            subtitle=f"Operational departments for {context_result.data.display_name}.",
            empty_state="No departments yet. Add the first department for this organization.",
            no_results_state="No departments match your current filters.",
            items=tuple(
                self._serialize_department(
                    row,
                    site_lookup=site_lookup,
                    department_lookup=department_lookup,
                    employee_lookup=employee_lookup,
                    organization_name=context_result.data.display_name,
                )
                for row in department_page.items
            ),
            paginated=True,
            page=department_page.page,
            page_size=department_page.page_size,
            total_count=department_page.total,
            filtered_total=department_page.filtered_total,
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
        Departments page for Organization Detail's Departments tab -- works
        regardless of which organization is currently active in the
        caller's session."""
        if self._department_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle="Departments appear here once the platform department API is connected.",
                empty_state="Platform department API is not connected in this QML preview.",
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

        result = self._department_api.list_departments_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load departments."
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        department_page = result.data
        site_lookup = self._site_lookup_for_organization(organization_id)
        department_lookup = self._department_lookup_for_organization(organization_id)
        employee_lookup = self._employee_lookup_for_organization(organization_id)
        return PlatformWorkspaceActionListViewModel(
            title="Departments",
            subtitle="Operational departments for this organization.",
            empty_state="No departments yet. Add the first department for this organization.",
            no_results_state="No departments match your current filters.",
            items=tuple(
                self._serialize_department(
                    row,
                    site_lookup=site_lookup,
                    department_lookup=department_lookup,
                    employee_lookup=employee_lookup,
                )
                for row in department_page.items
            ),
            paginated=True,
            page=department_page.page,
            page_size=department_page.page_size,
            total_count=department_page.total,
            filtered_total=department_page.filtered_total,
        )

    def build_catalog_page_for_site(
        self,
        site_id: str,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Explicit site_id-scoped, paginated Departments read for Site
        Detail's own Departments tab -- the paginated counterpart to
        build_catalog_for_site() above, for the canonical DataTable +
        TablePaginationBar workspace pattern. organization_id is required
        the same way it is for build_catalog_page_for_organization (the
        backend read is tenant-scoped-by-organization, not ambient-active-
        organization-scoped), so this works correctly regardless of which
        organization/site is active in the caller's session."""
        if self._department_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle="Departments appear here once the platform department API is connected.",
                empty_state="Platform department API is not connected in this QML preview.",
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

        result = self._department_api.list_departments_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
            site_id=site_id,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load departments."
            return PlatformWorkspaceActionListViewModel(
                title="Departments",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        department_page = result.data
        site_lookup = self._site_lookup_for_organization(organization_id)
        department_lookup = self._department_lookup_for_organization(organization_id)
        employee_lookup = self._employee_lookup_for_organization(organization_id)
        return PlatformWorkspaceActionListViewModel(
            title="Departments",
            subtitle="Departments assigned to this site.",
            empty_state="No departments assigned to this site.",
            no_results_state="No departments match your current filters.",
            items=tuple(
                self._serialize_department(
                    row,
                    site_lookup=site_lookup,
                    department_lookup=department_lookup,
                    employee_lookup=employee_lookup,
                )
                for row in department_page.items
            ),
            paginated=True,
            page=department_page.page,
            page_size=department_page.page_size,
            total_count=department_page.total,
            filtered_total=department_page.filtered_total,
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

    def build_head_of_department_options(self, department_id: str | None = None) -> tuple[dict[str, str], ...]:
        """HOD candidates are this exact department's own employees, not the
        organization at large -- head_of_department_employee_id is only
        valid when employee.department_id == department_id (the relationship
        itself is the HOD designation; there is no separate eligibility
        flag). A department with no id yet (Create, before any employee can
        reference it) has no possible candidates."""
        if self._employee_api is None or not department_id:
            return ()
        result = self._employee_api.list_employees(active_only=True, department_id=department_id)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=row.full_name,
                value=row.id,
                supporting_text=row.title or row.employee_code,
            )
            for row in result.data
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        """Suggest a unique department code (DEPT-<NAME>-0001 / DEPT-<YEAR>-0001)."""
        from src.core.platform.common.code_generation import CodeGenerator

        existing: set[str] = set()
        if self._department_api is not None:
            result = self._department_api.list_departments(active_only=None)
            if result.ok and result.data is not None:
                existing = {str(getattr(row, "department_code", "") or "").upper() for row in result.data}
        name = string_value(payload, "name")
        return CodeGenerator().generate(
            "department",
            exists=lambda code: code.upper() in existing,
            name=name or None,
            use_year=not bool(name),
        )

    def create_department(self, payload: dict[str, Any]) -> DesktopApiResult[DepartmentDto]:
        """Profile fields only -- lifecycle is never settable from Create;
        every new department starts ACTIVE (DepartmentCreateCommand's own
        default). Use activate_department/deactivate_department instead."""
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.create_department(
            DepartmentCreateCommand(
                department_code=string_value(payload, "departmentCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                site_id=optional_string_value(payload, "siteId"),
                parent_department_id=optional_string_value(payload, "parentDepartmentId"),
                department_type=string_value(payload, "departmentType"),
                cost_center_code=string_value(payload, "costCenterCode"),

                head_of_department_employee_id=string_value(payload, "headOfDepartmentEmployeeId"),
                notes=string_value(payload, "notes"),
            )
        )

    def update_department(self, payload: dict[str, Any]) -> DesktopApiResult[DepartmentDto]:
        """Pure profile update -- lifecycle is never settable from Edit; use
        activate_department/deactivate_department instead."""
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.update_department(
            DepartmentUpdateCommand(
                department_id=string_value(payload, "departmentId"),
                department_code=string_value(payload, "departmentCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                site_id=optional_string_value(payload, "siteId"),
                parent_department_id=optional_string_value(payload, "parentDepartmentId"),
                department_type=string_value(payload, "departmentType"),
                cost_center_code=string_value(payload, "costCenterCode"),

                head_of_department_employee_id=string_value(payload, "headOfDepartmentEmployeeId"),
                notes=string_value(payload, "notes"),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def activate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.activate_department(department_id)

    def deactivate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        if self._department_api is None:
            return preview_error_result("Platform department API is not connected in this QML preview.")
        return self._department_api.deactivate_department(department_id)

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

    def _site_lookup_for_organization(self, organization_id: str, *, max_pages: int = 20) -> dict[str, str]:
        """Same purpose as _site_lookup(), but tenant-scoped to a specific
        (possibly non-active) organization, for the Organization Detail
        Departments tab. Paginates through every site page (capped at
        max_pages * 100 records) rather than a single page, so large site
        catalogs still resolve every department's site name correctly."""
        if self._site_api is None:
            return {}
        lookup: dict[str, str] = {}
        page = 1
        while page <= max_pages:
            result = self._site_api.list_sites_page_for_organization(
                organization_id, page=page, page_size=100, active_only=None,
            )
            if not result.ok or result.data is None:
                break
            for row in result.data.items:
                lookup[row.id] = row.name
            if page * 100 >= result.data.total:
                break
            page += 1
        return lookup

    def _department_lookup_for_organization(self, organization_id: str, *, max_pages: int = 20) -> dict[str, str]:
        """Resolves parent_department_id -> parent department name,
        tenant-scoped to a specific (possibly non-active) organization."""
        if self._department_api is None:
            return {}
        lookup: dict[str, str] = {}
        page = 1
        while page <= max_pages:
            result = self._department_api.list_departments_page_for_organization(
                organization_id, page=page, page_size=100, active_only=None,
            )
            if not result.ok or result.data is None:
                break
            for row in result.data.items:
                lookup[row.id] = row.name
            if page * 100 >= result.data.total:
                break
            page += 1
        return lookup

    def _employee_lookup(self) -> dict[str, str]:
        """Employee id -> full name, active-organization-scoped, for
        resolving Head of Department display names. QML never resolves an
        Employee ID to a name itself -- this presenter always hands over an
        already-resolved headOfDepartmentDisplay string."""
        if self._employee_api is None:
            return {}
        result = self._employee_api.list_employees(active_only=None)
        if not result.ok or result.data is None:
            return {}
        return {row.id: row.full_name for row in result.data}

    def _employee_lookup_for_organization(self, organization_id: str, *, max_pages: int = 20) -> dict[str, str]:
        """Same purpose as _employee_lookup(), but tenant-scoped to a
        specific (possibly non-active) organization, for Organization/Site
        Detail's own Departments tabs."""
        if self._employee_api is None:
            return {}
        lookup: dict[str, str] = {}
        page = 1
        while page <= max_pages:
            result = self._employee_api.list_employees_page_for_organization(
                organization_id, page=page, page_size=100, active_only=None,
            )
            if not result.ok or result.data is None:
                break
            for row in result.data.items:
                lookup[row.id] = row.full_name
            if page * 100 >= result.data.total:
                break
            page += 1
        return lookup

    @staticmethod
    def _serialize_department(
        row: DepartmentDto,
        *,
        site_lookup: dict[str, str],
        department_lookup: dict[str, str] | None = None,
        employee_lookup: dict[str, str] | None = None,
        organization_name: str = "",
    ) -> PlatformWorkspaceActionItemViewModel:
        site_label = site_lookup.get(row.site_id or "", "No site")
        parent_label = (department_lookup or {}).get(row.parent_department_id or "", "")
        head_of_department_label = (employee_lookup or {}).get(row.head_of_department_employee_id or "", "")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.name,
            status_label=_department_status_label(row.is_active),
            subtitle=f"{row.department_code} | {row.department_type or 'Department'}",
            supporting_text=f"Site: {site_label}",
            # Raw value only -- the "Cost Center Code" column/field label
            # already provides context; do not re-embed the label inside
            # the string itself.
            meta_text=row.cost_center_code or "-",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "departmentId": row.id,
                "organizationId": row.organization_id,
                "organizationName": organization_name,
                "departmentCode": row.department_code,
                "name": row.name,
                "description": row.description,
                "siteId": row.site_id or "",
                "siteName": site_label,
                "parentDepartmentId": row.parent_department_id or "",
                "parentDepartmentName": parent_label,
                "departmentType": row.department_type,
                "costCenterCode": row.cost_center_code,
                "headOfDepartmentEmployeeId": row.head_of_department_employee_id or "",
                "headOfDepartmentDisplay": head_of_department_label,
                "notes": row.notes,
                "isActive": row.is_active,
                "version": row.version,
                "createdAt": row.created_at.isoformat() if row.created_at else "",
                "updatedAt": row.updated_at.isoformat() if row.updated_at else "",
            },
        )

__all__ = ["PlatformDepartmentCatalogPresenter"]
