from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.org.contracts import (
    DepartmentRepository,
    LinkedEmployeeResource,
    LinkedEmployeeResourceRepository,
    OrganizationRepository,
    SiteRepository,
)
from src.core.platform.org.domain import Employee
from src.core.platform.org.support import employee_contact


def build_employee_audit_details(employee: Employee) -> dict[str, str]:
    return {
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "department_id": employee.department_id or "",
        "department": employee.department,
        "site_id": employee.site_id or "",
        "site_name": employee.site_name,
        "title": employee.title,
        "is_active": str(employee.is_active),
    }


def sync_linked_employee_resources(
    employee: Employee,
    resource_repo: LinkedEmployeeResourceRepository | None,
) -> None:
    if resource_repo is None:
        return
    for resource in resource_repo.list_by_employee(employee.id):
        if _worker_type_code(resource) != "employee":
            continue
        resource.name = employee.full_name
        if employee.title:
            resource.role = employee.title
        resource.contact = employee_contact(employee)
        resource_repo.update(resource)
        domain_events.resources_changed.emit(resource.id)


def _worker_type_code(resource: LinkedEmployeeResource) -> str:
    worker_type = getattr(resource, "worker_type", None)
    normalized = getattr(worker_type, "value", worker_type)
    return str(normalized or "").strip().lower()


def resolve_employee_site_reference(
    *,
    site_repo: SiteRepository | None,
    organization_repo: OrganizationRepository | None,
    site_id: str | None,
    site_name: str,
) -> tuple[str | None, str]:
    normalized_id = (site_id or "").strip() or None
    normalized_name = (site_name or "").strip()
    site = _load_site(site_repo=site_repo, organization_repo=organization_repo, site_id=normalized_id)
    if site is not None:
        return site.id, site.name
    matched = _match_site_by_name(
        site_repo=site_repo,
        organization_repo=organization_repo,
        site_name=normalized_name,
    )
    if matched is not None:
        return matched.id, matched.name
    return None, normalized_name


def resolve_employee_department_reference(
    *,
    department_repo: DepartmentRepository | None,
    organization_repo: OrganizationRepository | None,
    department_id: str | None,
    department_name: str,
) -> tuple[str | None, str]:
    normalized_id = (department_id or "").strip() or None
    normalized_name = (department_name or "").strip()
    department = _load_department(
        department_repo=department_repo,
        organization_repo=organization_repo,
        department_id=normalized_id,
    )
    if department is not None:
        return department.id, department.name
    matched = _match_department_by_name(
        department_repo=department_repo,
        organization_repo=organization_repo,
        department_name=normalized_name,
    )
    if matched is not None:
        return matched.id, matched.name
    return None, normalized_name


def _load_site(
    *,
    site_repo: SiteRepository | None,
    organization_repo: OrganizationRepository | None,
    site_id: str | None,
):
    if site_id is None or site_repo is None:
        return None
    site = site_repo.get(site_id)
    if site is None or not _belongs_to_active_organization(
        organization_repo=organization_repo,
        organization_id=getattr(site, "organization_id", None),
    ):
        raise ValidationError("Employee site must belong to the active organization.", code="EMPLOYEE_SITE_INVALID")
    return site


def _load_department(
    *,
    department_repo: DepartmentRepository | None,
    organization_repo: OrganizationRepository | None,
    department_id: str | None,
):
    if department_id is None or department_repo is None:
        return None
    department = department_repo.get(department_id)
    if department is None or not _belongs_to_active_organization(
        organization_repo=organization_repo,
        organization_id=getattr(department, "organization_id", None),
    ):
        raise ValidationError(
            "Employee department must belong to the active organization.",
            code="EMPLOYEE_DEPARTMENT_INVALID",
        )
    return department


def _match_site_by_name(
    *,
    site_repo: SiteRepository | None,
    organization_repo: OrganizationRepository | None,
    site_name: str,
):
    normalized = (site_name or "").strip().lower()
    active_organization_id = _active_organization_id(organization_repo)
    if not normalized or active_organization_id is None or site_repo is None:
        return None
    matches = [
        site
        for site in site_repo.list_for_organization(active_organization_id, active_only=True)
        if (site.name or "").strip().lower() == normalized
    ]
    return matches[0] if len(matches) == 1 else None


def _match_department_by_name(
    *,
    department_repo: DepartmentRepository | None,
    organization_repo: OrganizationRepository | None,
    department_name: str,
):
    normalized = (department_name or "").strip().lower()
    active_organization_id = _active_organization_id(organization_repo)
    if not normalized or active_organization_id is None or department_repo is None:
        return None
    matches = [
        department
        for department in department_repo.list_for_organization(active_organization_id, active_only=True)
        if (department.name or "").strip().lower() == normalized
    ]
    return matches[0] if len(matches) == 1 else None


def _active_organization_id(organization_repo: OrganizationRepository | None) -> str | None:
    if organization_repo is None:
        return None
    organization = organization_repo.get_active()
    return organization.id if organization is not None else None


def _belongs_to_active_organization(
    *,
    organization_repo: OrganizationRepository | None,
    organization_id: str | None,
) -> bool:
    active_organization_id = _active_organization_id(organization_repo)
    if active_organization_id is None:
        return True
    return organization_id == active_organization_id


__all__ = [
    "build_employee_audit_details",
    "resolve_employee_department_reference",
    "resolve_employee_site_reference",
    "sync_linked_employee_resources",
]
