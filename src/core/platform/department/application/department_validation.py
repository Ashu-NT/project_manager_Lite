from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError

from .department_utils import normalize_optional_text


def validate_site_id(service, site_id: str | None, *, organization_id: str) -> str | None:
    normalized = normalize_optional_text(site_id) or None
    if normalized is None or service._site_repo is None:
        return normalized
    site = service._site_repo.get(normalized)
    if site is None or site.organization_id != organization_id:
        raise ValidationError(
            "Department site must belong to the active organization.",
            code="DEPARTMENT_SITE_INVALID",
        )
    return normalized


def validate_parent_department_id(
    service,
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
    parent = service._department_repo.get(normalized)
    if parent is None or parent.organization_id != organization_id:
        raise ValidationError(
            "Parent department must belong to the active organization.",
            code="DEPARTMENT_PARENT_INVALID",
        )
    return normalized


def validate_manager_employee_id(service, manager_employee_id: str | None) -> str | None:
    normalized = normalize_optional_text(manager_employee_id) or None
    if normalized is None or service._employee_repo is None:
        return normalized
    if service._employee_repo.get(normalized) is None:
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
