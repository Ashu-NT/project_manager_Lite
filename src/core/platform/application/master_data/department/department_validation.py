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
    if current_department_id:
        _require_no_ancestry_cycle(
            department_repo,
            proposed_parent_id=normalized,
            current_department_id=current_department_id,
        )
    return normalized


def _require_no_ancestry_cycle(
    department_repo: DepartmentRepository,
    *,
    proposed_parent_id: str,
    current_department_id: str,
) -> None:
    """Rejects not just a direct self-parent (checked separately, above)
    but any transitive cycle -- e.g. assigning C's parent to A when A's own
    parent chain already runs back through C (A -> B -> C). Walks the
    proposed parent's ancestor chain looking for `current_department_id`;
    a `visited` set makes this safe even against a pre-existing malformed
    cycle in the data (terminates rather than looping forever)."""
    visited: set[str] = set()
    cursor: str | None = proposed_parent_id
    while cursor is not None:
        if cursor == current_department_id:
            raise ValidationError(
                "Department hierarchy cannot contain a cycle.",
                code="DEPARTMENT_PARENT_CYCLE",
            )
        if cursor in visited:
            # Pre-existing malformed cycle elsewhere in the data, unrelated
            # to the department being updated -- stop rather than loop
            # forever; this proposed parent doesn't cycle back to
            # current_department_id, so it's not this validation's concern.
            return
        visited.add(cursor)
        ancestor = department_repo.get(cursor)
        cursor = ancestor.parent_department_id if ancestor is not None else None


def validate_head_of_department_employee_id(
    employee_repo: EmployeeRepository | None, head_of_department_employee_id: str | None, *, organization_id: str
) -> str | None:
    normalized = normalize_optional_text(head_of_department_employee_id) or None
    if normalized is None or employee_repo is None:
        return normalized
    if employee_repo.get_for_organization(normalized, organization_id) is None:
        raise ValidationError(
            "Department Head of Department must reference an existing employee.",
            code="DEPARTMENT_HEAD_OF_DEPARTMENT_INVALID",
        )
    return normalized


__all__ = [
    "validate_head_of_department_employee_id",
    "validate_parent_department_id",
    "validate_site_id",
]
