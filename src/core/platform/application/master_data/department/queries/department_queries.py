from __future__ import annotations

from dataclasses import dataclass, field

from src.core.platform.access.authorization import filter_scope_rows
from src.core.platform.application.master_data.department.department_access import (
    require_department_read_access,
)
from src.core.platform.application.master_data.department.department_context import (
    active_organization,
)
from src.core.platform.application.master_data.department.department_utils import (
    normalize_optional_text,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.domain.master_data.department import Department
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.org.support import normalize_code
from src.core.platform.domain.security.auth.session import UserSessionContext

_DEFAULT_DEPARTMENT_PAGE_SIZE = 25
DEPARTMENT_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class DepartmentPage:
    items: list[Department] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_DEPARTMENT_PAGE_SIZE


class DepartmentQueryHandler:
    """Department reads: active-organization lists and lookups, the overview
    rollup, and the tenant-scoped page for any organization."""

    def __init__(
        self,
        *,
        department_repo: DepartmentRepository,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        overview_rollup_reader: PlatformOverviewRollupReader | None,
    ) -> None:
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader

    def list_departments(
        self, *, active_only: bool | None = None, site_id: str | None = None
    ) -> list[Department]:
        require_department_read_access(self._user_session, "list departments")
        organization = active_organization(self._tenant_context_service)
        return self._department_repo.list_for_organization(
            organization.id, active_only=active_only, site_id=site_id
        )

    def search_departments(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Department]:
        require_department_read_access(self._user_session, "search departments")
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self._department_repo.list_for_organization(
            active_organization(self._tenant_context_service).id, active_only=active_only
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

    def get_department(self, department_id: str) -> Department:
        require_department_read_access(self._user_session, "view department")
        organization = active_organization(self._tenant_context_service)
        department = self._department_repo.get(department_id)
        if department is None or department.organization_id != organization.id:
            raise NotFoundError(
                "Department not found in the active organization.",
                code="DEPARTMENT_NOT_FOUND",
            )
        return department

    def find_department_by_code(self, department_code: str) -> Department | None:
        require_department_read_access(self._user_session, "resolve department")
        normalized_code = normalize_code(department_code, label="Department code")
        return self._department_repo.get_by_code(active_organization(self._tenant_context_service).id, normalized_code)

    def get_context_organization(self) -> Organization:
        require_permission(
            self._user_session, "settings.manage", operation_label="view department context"
        )
        return active_organization(self._tenant_context_service)

    def get_department_rollup_summary(self) -> DepartmentRollupSummary:
        require_department_read_access(self._user_session, "view department rollup summary")
        organization = active_organization(self._tenant_context_service)
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view department rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_department_summary(
            organization_id=organization.id,
            tenant_id=tenant_id,
        )

    def list_departments_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_DEPARTMENT_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> DepartmentPage:
        """Tenant-scoped read for ANY organization in the caller's tenant --
        unlike list_departments()/search_departments(), not limited to the
        session's active organization. For Organization Detail's
        Departments tab, where an admin may be viewing an organization they
        haven't switched into.

        Read-only: never used by create/update/delete, which keep using
        active_organization(self._tenant_context_service) (the existing, unchanged domain rule).
        Never gates on the organization's own lifecycle status -- inactive
        and archived organizations' department history remains readable
        here.
        """
        require_department_read_access(self._user_session, "list departments")
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Tenant context is required to list departments.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list departments for organization"
        )
        target_organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if target_organization is None:
            raise NotFoundError(
                "Organization not found in the current tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in DEPARTMENT_PAGE_SIZE_OPTIONS else _DEFAULT_DEPARTMENT_PAGE_SIZE
        )
        items, total, filtered_total = self._department_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            active_only=active_only,
            site_id=site_id,
        )
        items = filter_scope_rows(
            items,
            self._user_session,
            scope_type="department",
            permission_code="department.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )
        return DepartmentPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )


__all__ = ["DEPARTMENT_PAGE_SIZE_OPTIONS", "DepartmentPage", "DepartmentQueryHandler"]
