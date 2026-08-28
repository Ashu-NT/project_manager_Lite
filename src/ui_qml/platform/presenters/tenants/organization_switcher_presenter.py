from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.master_data.org.models.organization import OrganizationDto
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.ui_qml.platform.presenters.common.presenter_support_helpers import preview_error_result
from src.ui_qml.platform.view_models.tenants.organization import OrganizationSwitcherItemViewModel


class OrganizationSwitcherPresenter:
    """Transforms PlatformTenantDesktopApi's organization-switcher responses into view models.

    Session/working-context only -- never organization availability (enable/disable) or
    organization-scoped access grants, which stay on their own workspaces (P10A/P10B)."""

    def __init__(self, *, tenant_api: PlatformTenantDesktopApi | None = None) -> None:
        self._tenant_api = tenant_api

    def build_organization_list(self) -> tuple[OrganizationSwitcherItemViewModel, ...]:
        if self._tenant_api is None:
            return ()
        result = self._tenant_api.list_accessible_organizations()
        if not result.ok or result.data is None:
            return ()
        return tuple(self._serialize_item(o) for o in result.data)

    def get_active_organization_id(self) -> str:
        if self._tenant_api is None:
            return ""
        result = self._tenant_api.get_active_organization()
        if result.ok and result.data is not None:
            return result.data.id
        return ""

    def switch_to_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._tenant_api is None:
            return preview_error_result("Tenant API is not connected.")
        return self._tenant_api.switch_to_organization(organization_id)

    @staticmethod
    def _serialize_item(o: OrganizationDto) -> OrganizationSwitcherItemViewModel:
        return OrganizationSwitcherItemViewModel(
            id=o.id,
            display_name=o.display_name,
            organization_code=o.organization_code,
            is_enabled=o.is_enabled,
        )


__all__ = ["OrganizationSwitcherPresenter"]
