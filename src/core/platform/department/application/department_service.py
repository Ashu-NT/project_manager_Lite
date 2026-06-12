from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.department.contracts import DepartmentRepository
from src.core.platform.department.domain import Department
from src.core.platform.employee.contracts import EmployeeRepository
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.core.platform.site.contracts import LocationReferenceRepository, SiteRepository
from src.core.platform.tenancy import TenantContextService

from . import department_commands as _cmd
from . import department_queries as _queries
from .department_location_service import (
    list_available_location_references as _list_location_refs,
    register_location_reference_repository as _register_location_repo,
)


class DepartmentService:
    def __init__(
        self,
        session: Session,
        department_repo: DepartmentRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        location_reference_repo: LocationReferenceRepository | None = None,
        user_session=None,
        audit_service=None,
        tenant_context_service: TenantContextService | None = None,
    ):
        self._session = session
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._employee_repo = employee_repo
        self._location_reference_repo = location_reference_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._tenant_context_service = tenant_context_service

    def register_location_reference_repository(
        self,
        location_reference_repo: LocationReferenceRepository | None,
    ) -> None:
        _register_location_repo(self, location_reference_repo)

    def list_departments(self, *, active_only: bool | None = None) -> list[Department]:
        return _queries.list_departments(self, active_only=active_only)

    def search_departments(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Department]:
        return _queries.search_departments(self, search_text=search_text, active_only=active_only)

    def get_department(self, department_id: str) -> Department:
        return _queries.get_department(self, department_id)

    def find_department_by_code(self, department_code: str) -> Department | None:
        return _queries.find_department_by_code(self, department_code)

    def get_context_organization(self) -> Organization:
        return _queries.get_context_organization(self)

    def list_available_location_references(
        self,
        *,
        site_id: str | None = None,
        active_only: bool | None = True,
    ) -> list[object]:
        return _list_location_refs(self, site_id=site_id, active_only=active_only)

    def create_department(
        self,
        *,
        department_code: str,
        name: str | None = None,
        display_name: str | None = None,
        description: str = "",
        site_id: str | None = None,
        default_location_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str = "",
        cost_center_code: str = "",
        manager_employee_id: str | None = None,
        is_active: bool = True,
        notes: str = "",
    ) -> Department:
        return _cmd.create_department(
            self,
            department_code=department_code,
            name=name,
            display_name=display_name,
            description=description,
            site_id=site_id,
            default_location_id=default_location_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            manager_employee_id=manager_employee_id,
            is_active=is_active,
            notes=notes,
        )

    def update_department(
        self,
        department_id: str,
        *,
        department_code: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        site_id: str | None = None,
        default_location_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str | None = None,
        cost_center_code: str | None = None,
        manager_employee_id: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Department:
        return _cmd.update_department(
            self,
            department_id,
            department_code=department_code,
            name=name,
            display_name=display_name,
            description=description,
            site_id=site_id,
            default_location_id=default_location_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            manager_employee_id=manager_employee_id,
            is_active=is_active,
            notes=notes,
            expected_version=expected_version,
        )


__all__ = ["DepartmentService"]
