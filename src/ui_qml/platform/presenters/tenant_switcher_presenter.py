from __future__ import annotations

from src.api.desktop.platform.models import DesktopApiResult
from src.core.platform.api.desktop.tenant.tenancy.models.tenant import TenantDto
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.ui_qml.platform.presenters.support import preview_error_result
from src.ui_qml.platform.view_models.tenant import TenantSwitcherItemViewModel


class TenantSwitcherPresenter:
    """Transforms PlatformTenantDesktopApi responses into view models."""

    def __init__(self, *, tenant_api: PlatformTenantDesktopApi | None = None) -> None:
        self._tenant_api = tenant_api

    def build_tenant_list(self) -> tuple[TenantSwitcherItemViewModel, ...]:
        if self._tenant_api is None:
            return ()
        result = self._tenant_api.list_accessible_tenants()
        if not result.ok or result.data is None:
            return ()
        return tuple(self._serialize_item(t) for t in result.data)

    def get_active_tenant_id(self) -> str:
        if self._tenant_api is None:
            return ""
        result = self._tenant_api.get_active_tenant()
        if result.ok and result.data is not None:
            return result.data.id
        return ""

    def switch_to_tenant(self, tenant_id: str) -> DesktopApiResult[TenantDto]:
        if self._tenant_api is None:
            return preview_error_result("Tenant API is not connected.")
        return self._tenant_api.switch_to_tenant(tenant_id)

    @staticmethod
    def _serialize_item(t: TenantDto) -> TenantSwitcherItemViewModel:
        return TenantSwitcherItemViewModel(
            id=t.id,
            display_name=t.display_name,
            tenant_code=t.tenant_code,
            tenant_status=t.tenant_status,
            is_active=t.is_active,
        )


__all__ = ["TenantSwitcherPresenter"]
