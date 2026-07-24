from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import DesktopApiResult
from src.api.desktop.platform.models.tenant import TenantDto
from src.core.platform.tenancy.application.tenant_admin_service import TenantAdminService
from src.core.platform.tenancy.domain.tenant import Tenant
from src.core.platform.tenancy.tenant_context import TenantContextService


class PlatformTenantDesktopApi:
    """Desktop-facing adapter for tenant switching and listing accessible tenants."""

    def __init__(
        self,
        *,
        tenant_admin_service: TenantAdminService,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._tenant_admin_service = tenant_admin_service
        self._tenant_context_service = tenant_context_service

    def list_accessible_tenants(self) -> DesktopApiResult[tuple[TenantDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_tenant(t)
                for t in self._tenant_admin_service.list_accessible_tenants()
            )
        )

    def get_active_tenant(self) -> DesktopApiResult[TenantDto | None]:
        return execute_desktop_operation(
            lambda: self._serialize_tenant(tenant)
            if (tenant := self._tenant_context_service.get_active_tenant()) is not None
            else None
        )

    def switch_to_tenant(self, tenant_id: str) -> DesktopApiResult[TenantDto]:
        return execute_desktop_operation(
            lambda: self._serialize_tenant(
                self._tenant_context_service.switch_to_tenant(tenant_id)
            )
        )

    @staticmethod
    def _serialize_tenant(tenant: Tenant) -> TenantDto:
        return TenantDto(
            id=tenant.id,
            tenant_code=tenant.tenant_code,
            display_name=tenant.display_name,
            tenant_status=tenant.tenant_status,
            is_active=tenant.is_active,
        )


__all__ = ["PlatformTenantDesktopApi"]
