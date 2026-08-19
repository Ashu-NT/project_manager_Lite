from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadPage,
    ResourceCatalogReader,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class ResourceQueryMixin:
    _resource_repo: ResourceRepository
    _resource_catalog_reader: ResourceCatalogReader | None

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
                "utilizationValue",
            },
            default_key="catalog",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="list resource catalog"
        )
        read_kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            search_text=str(search_text or "").strip(),
            active=active,
            category=category,
            page=page_request.page,
            page_size=page_request.page_size,
            sort=sort,
        )
        result = self._resource_catalog_reader.read_page(**read_kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._resource_catalog_reader.read_page(**read_kwargs)
        return result

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
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)


__all__ = ["ResourceQueryMixin"]
