from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReader,
    ResourceCatalogReadPage,
    ResourceInspectorFact,
    ResourceInspectorReader,
    ResourceSummaryFact,
    ResourceSummaryReader,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.application.security.authorization.enforcement.session_authorization_engine import (
    get_authorization_engine,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.security.auth.session import UserSessionContext


class ResourceQueryHandler(ProjectManagementModuleGuardMixin):
    """Resource master-data reads (catalog, inspector, summary, workspace lists)."""

    def __init__(
        self,
        *,
        resource_repo: ResourceRepository,
        user_session: UserSessionContext | None = None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        resource_catalog_reader: ResourceCatalogReader | None = None,
        resource_inspector_reader: ResourceInspectorReader | None = None,
        resource_summary_reader: ResourceSummaryReader | None = None,
    ) -> None:
        self._resource_repo = resource_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._resource_catalog_reader = resource_catalog_reader
        self._resource_inspector_reader = resource_inspector_reader
        self._resource_summary_reader = resource_summary_reader

    def list_resources(self) -> list[Resource]:
        require_permission(self._user_session, "resource.read", operation_label="list resources")
        return self._resource_repo.list()

    def query_catalog_page(
        self,
        *,
        search_text: str = "",
        active: bool | None = None,
        category: CostType | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "catalog",
        sort_direction: str = "asc",
    ) -> ResourceCatalogReadPage:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="list resource catalog",
        )
        if self._resource_catalog_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Resource catalog reader is not configured.")
        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "title",
                "resourceCode",
                "statusLabel",
                "department",
                "site",
                "role",
                "workerTypeLabel",
                "capacityPercent",
            },
            default_key="catalog",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="list resource catalog"
        )
        reader = self._resource_catalog_reader
        normalized_search = str(search_text or "").strip()

        def _read_page(page_number: int) -> ResourceCatalogReadPage:
            return reader.read_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                search_text=normalized_search,
                active=active,
                category=category,
                page=page_number,
                page_size=page_request.page_size,
                sort=sort,
            )

        result = _read_page(page_request.page)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            result = _read_page(normalized_page)
        return result

    def get_resource_inspector(self, resource_id: str) -> ResourceInspectorFact:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="view resource inspector",
        )
        if self._resource_inspector_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Resource Inspector reader is not configured.")
        normalized_id = str(resource_id or "").strip()
        if not normalized_id:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view resource inspector"
        )
        fact = self._resource_inspector_reader.read_inspector(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=normalized_id,
        )
        if fact is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        can_manage = get_authorization_engine().has_permission(
            self._user_session,
            "resource.manage",
            resource=fact,
        )
        return replace(
            fact,
            can_read=True,
            can_manage=can_manage,
            can_deactivate=can_manage and fact.is_active,
            can_reactivate=can_manage and not fact.is_active,
        )

    def get_resource_summary(self, resource_id: str) -> ResourceSummaryFact:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="view resource summary",
        )
        if self._resource_summary_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Resource summary reader is not configured.")
        normalized_id = str(resource_id or "").strip()
        if not normalized_id:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view resource summary"
        )
        fact = self._resource_summary_reader.read_summary(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=normalized_id,
        )
        if fact is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        can_manage = get_authorization_engine().has_permission(
            self._user_session,
            "resource.manage",
            resource=fact,
        )
        return replace(fact, can_read=True, can_manage=can_manage)

    def list_for_project_workspace(
        self,
        project_id: str,
        *,
        resource_ids: tuple[str, ...] = (),
    ) -> list[Resource]:
        require_any_project_permission(
            self._user_session,
            project_id,
            ("project.read", "project.manage"),
            operation_label="list project resources",
        )
        self._active_organization_id(operation_label="list project resources")
        normalized_ids = {
            str(resource_id or "").strip()
            for resource_id in resource_ids
            if str(resource_id or "").strip()
        }
        if not normalized_ids:
            return self._resource_repo.list()
        return self._resource_repo.list_by_ids(list(normalized_ids))

    def list_for_task_workspace(
        self,
        *,
        resource_ids: tuple[str, ...],
    ) -> list[Resource]:
        require_any_permission(
            self._user_session,
            ("resource.read", "task.read", "task.manage"),
            operation_label="list task resources",
        )
        self._active_organization_id(operation_label="list task resources")
        normalized_ids = {
            str(resource_id or "").strip()
            for resource_id in resource_ids
            if str(resource_id or "").strip()
        }
        if not normalized_ids:
            return []
        return self._resource_repo.list_by_ids(list(normalized_ids))

    def get_resource(self, resource_id: str) -> Resource:
        require_permission(self._user_session, "resource.read", operation_label="view resource")
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        return resource

    def _active_organization_id(self, *, operation_label: str) -> str:
        tenant_context = self._tenant_context_service
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)


__all__ = ["ResourceQueryHandler"]
