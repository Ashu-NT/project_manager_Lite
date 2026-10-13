from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.domain.master_data.department import Department
from src.core.platform.domain.master_data.site import Site


def resolve_employee_site_reference(
    *,
    site_repo: SiteRepository | None,
    organization_repo: OrganizationRepository | None,
    active_organization_id: str | None = None,
    site_id: str | None,
    site_name: str,
) -> tuple[str | None, str]:
    normalized_id = (site_id or "").strip() or None
    normalized_name = (site_name or "").strip()
    site = _load_site(
        site_repo=site_repo,
        active_organization_id=active_organization_id,
        site_id=normalized_id,
    )
    if site is not None:
        return site.id, site.name
    matched = _match_site_by_name(
        site_repo=site_repo,
        active_organization_id=active_organization_id,
        site_name=normalized_name,
    )
    if matched is not None:
        return matched.id, matched.name
    return None, normalized_name


def resolve_employee_site_for_department(
    *,
    department: Department,
    site_repo: SiteRepository | None,
    organization_repo: OrganizationRepository | None,
    active_organization_id: str | None = None,
    site_id: str | None,
    site_name: str,
    current_site_id: str | None = None,
    current_site_name: str = "",
) -> tuple[str | None, str]:
    """Resolve an Employee's site against its (already-resolved) Department,
    enforcing the final invariant: when a Department is itself bound to a
    Site, every one of its Employees must share that exact Site -- derived
    automatically when not explicitly given, and rejected outright if an
    explicit override contradicts it. When a Department has no Site (an
    organization-wide Department), an Employee may have any Site in the
    same organization, or none -- `current_site_id`/`current_site_name`
    (the employee's own existing values, empty for Create) are preserved
    when the caller supplies nothing this call, so a Department transfer
    into an organization-wide Department never silently invents or clears
    a Site that wasn't part of the request."""
    department_site_id = getattr(department, "site_id", None)
    requested_id = (site_id or "").strip() or None
    requested_name = (site_name or "").strip()

    if department_site_id:
        if requested_id and requested_id != department_site_id:
            raise ValidationError(
                "Employee site must match the selected department's site.",
                code="EMPLOYEE_SITE_DEPARTMENT_MISMATCH",
            )
        if requested_name and not requested_id:
            # A free-text site name was given with no id -- it must still
            # resolve to the department's own site, never a different one.
            resolved_id, _resolved_name = resolve_employee_site_reference(
                site_repo=site_repo,
                organization_repo=organization_repo,
                active_organization_id=active_organization_id,
                site_id=None,
                site_name=requested_name,
            )
            if resolved_id and resolved_id != department_site_id:
                raise ValidationError(
                    "Employee site must match the selected department's site.",
                    code="EMPLOYEE_SITE_DEPARTMENT_MISMATCH",
                )
        # Derive/default from the department -- covers both "nothing
        # provided" and "the same site explicitly provided" in one branch.
        # Department has no cached site_name of its own, so resolve the
        # real Site row for a display-ready name.
        department_site = _load_site(
            site_repo=site_repo,
            active_organization_id=active_organization_id,
            site_id=department_site_id,
        )
        return department_site_id, (department_site.name if department_site is not None else "")

    # Organization-wide department: any same-organization site is allowed,
    # or none. Only re-resolve when the caller actually supplied something
    # this call; otherwise preserve the current value untouched.
    if requested_id is not None or requested_name:
        return resolve_employee_site_reference(
            site_repo=site_repo,
            organization_repo=organization_repo,
            active_organization_id=active_organization_id,
            site_id=requested_id,
            site_name=requested_name,
        )
    return current_site_id, current_site_name


def resolve_employee_department_reference(
    *,
    department_repo: DepartmentRepository | None,
    organization_repo: OrganizationRepository | None,
    active_organization_id: str | None = None,
    department_id: str | None,
    department_name: str,
) -> tuple[str | None, str]:
    normalized_id = (department_id or "").strip() or None
    normalized_name = (department_name or "").strip()
    department = _load_department(
        department_repo=department_repo,
        active_organization_id=active_organization_id,
        department_id=normalized_id,
    )
    if department is not None:
        return department.id, department.name
    matched = _match_department_by_name(
        department_repo=department_repo,
        active_organization_id=active_organization_id,
        department_name=normalized_name,
    )
    if matched is not None:
        return matched.id, matched.name
    return None, normalized_name


def _load_site(
    *,
    site_repo: SiteRepository | None,
    active_organization_id: str | None,
    site_id: str | None,
) -> Site | None:
    if site_id is None or site_repo is None:
        return None
    site = site_repo.get(site_id)
    if site is None or not _belongs_to_active_organization(
        active_organization_id=active_organization_id,
        organization_id=getattr(site, "organization_id", None),
    ):
        raise ValidationError("Employee site must belong to the active organization.", code="EMPLOYEE_SITE_INVALID")
    return site


def _load_department(
    *,
    department_repo: DepartmentRepository | None,
    active_organization_id: str | None,
    department_id: str | None,
) -> Department | None:
    if department_id is None or department_repo is None:
        return None
    department = department_repo.get(department_id)
    if department is None or not _belongs_to_active_organization(
        active_organization_id=active_organization_id,
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
    active_organization_id: str | None,
    site_name: str,
) -> Site | None:
    normalized = (site_name or "").strip().lower()
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
    active_organization_id: str | None,
    department_name: str,
) -> Department | None:
    normalized = (department_name or "").strip().lower()
    if not normalized or active_organization_id is None or department_repo is None:
        return None
    matches = [
        department
        for department in department_repo.list_for_organization(active_organization_id, active_only=True)
        if (department.name or "").strip().lower() == normalized
    ]
    return matches[0] if len(matches) == 1 else None


def _belongs_to_active_organization(
    *,
    active_organization_id: str | None,
    organization_id: str | None,
) -> bool:
    if active_organization_id is None:
        return False
    return organization_id == active_organization_id


__all__ = [
    "resolve_employee_department_reference",
    "resolve_employee_site_for_department",
    "resolve_employee_site_reference",
]
