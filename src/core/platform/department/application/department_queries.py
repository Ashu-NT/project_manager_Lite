from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.department.domain import Department
from src.core.platform.org.domain import Organization
from src.core.platform.org.support import normalize_code

from .department_access import require_department_read_access
from .department_context import active_organization
from .department_utils import normalize_optional_text

if TYPE_CHECKING:
    from .department_service import DepartmentService


def list_departments(service: DepartmentService, *, active_only: bool | None = None) -> list[Department]:
    require_department_read_access(service, "list departments")
    organization = active_organization(service)
    return service._department_repo.list_for_organization(organization.id, active_only=active_only)


def search_departments(
    service: DepartmentService,
    *,
    search_text: str = "",
    active_only: bool | None = True,
) -> list[Department]:
    require_department_read_access(service, "search departments")
    normalized_search = normalize_optional_text(search_text).lower()
    rows = service._department_repo.list_for_organization(
        active_organization(service).id, active_only=active_only
    )
    if not normalized_search:
        return rows
    return [
        department
        for department in rows
        if normalized_search in " ".join(
            filter(
                None,
                [
                    department.department_code,
                    department.name,
                    department.department_type,
                    department.cost_center_code,
                    department.notes,
                ],
            )
        ).lower()
    ]


def get_department(service: DepartmentService, department_id: str) -> Department:
    require_department_read_access(service, "view department")
    organization = active_organization(service)
    department = service._department_repo.get(department_id)
    if department is None or department.organization_id != organization.id:
        raise NotFoundError(
            "Department not found in the active organization.",
            code="DEPARTMENT_NOT_FOUND",
        )
    return department


def find_department_by_code(service: DepartmentService, department_code: str) -> Department | None:
    require_department_read_access(service, "resolve department")
    normalized_code = normalize_code(department_code, label="Department code")
    return service._department_repo.get_by_code(active_organization(service).id, normalized_code)


def get_context_organization(service: DepartmentService) -> Organization:
    require_permission(
        service._user_session, "settings.manage", operation_label="view department context"
    )
    return active_organization(service)


__all__ = [
    "find_department_by_code",
    "get_context_organization",
    "get_department",
    "list_departments",
    "search_departments",
]
