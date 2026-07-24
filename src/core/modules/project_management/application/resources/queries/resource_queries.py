from __future__ import annotations

from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository


class ResourceQueryMixin:
    _resource_repo: ResourceRepository

    def list_resources(self) -> list[Resource]:
        require_permission(self._user_session, "resource.read", operation_label="list resources")
        return self._resource_repo.list()

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
