from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.master_data.department.contracts import DepartmentRepository
from src.core.platform.contract.repositories.master_data.employee.contracts import EmployeeRepository
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository

from .department_utils import normalize_optional_text


def validate_site_id(
    site_repo: SiteRepository | None, site_id: str | None, *, organization_id: str
) -> str | None:
    normalized = normalize_optional_text(site_id) or None
    if normalized is None or site_repo is None:
        return normalized
    site = site_repo.get(normalized)
    if site is None or site.organization_id != organization_id:
        raise ValidationError(
            "Department site must belong to the active organization.",
            code="DEPARTMENT_SITE_INVALID",
        )
    return normalized


def validate_parent_department_id(
    department_repo: DepartmentRepository,
    parent_department_id: str | None,
    *,
    organization_id: str,
    current_department_id: str | None = None,
) -> str | None:
    normalized = normalize_optional_text(parent_department_id) or None
    if normalized is None:
        return None
    if current_department_id and normalized == current_department_id:
        raise ValidationError("Department cannot be its own parent.", code="DEPARTMENT_PARENT_INVALID")
    parent = department_repo.get(normalized)
    if parent is None or parent.organization_id != organization_id:
        raise ValidationError(
            "Parent department must belong to the active organization.",
            code="DEPARTMENT_PARENT_INVALID",
        )
    return normalized


def validate_manager_employee_id(
    employee_repo: EmployeeRepository | None, manager_employee_id: str | None, *, organization_id: str
) -> str | None:
    normalized = normalize_optional_text(manager_employee_id) or None
    if normalized is None or employee_repo is None:
        return normalized
    if employee_repo.get_for_organization(normalized, organization_id) is None:
        raise ValidationError(
            "Department manager employee does not exist.",
            code="DEPARTMENT_MANAGER_INVALID",
        )
    return normalized


__all__ = [
    "validate_manager_employee_id",
    "validate_parent_department_id",
    "validate_site_id",
]
