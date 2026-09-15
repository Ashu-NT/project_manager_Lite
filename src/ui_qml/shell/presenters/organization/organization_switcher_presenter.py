from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.api.desktop.master_data.org.models.organization import OrganizationDto
from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi


@dataclass(frozen=True)
class OrganizationSwitcherItemViewModel:
    id: str
    display_name: str
    organization_code: str
    is_enabled: bool


class OrganizationSwitcherPresenter:
    """Shell-owned presenter for the global-header organization switcher.

    Deliberately a separate, independent consumer of PlatformTenantDesktopApi
    from Platform's own internal admin-dialog organization switcher -- the
    Desktop API is the shared boundary; this presentation layer is not.
    """

    def __init__(self, *, tenant_api: PlatformTenantDesktopApi | None = None) -> None:
        self._tenant_api = tenant_api

    def build_organization_list(self) -> tuple[OrganizationSwitcherItemViewModel, ...]:
        if self._tenant_api is None:
            return ()
        result = self._tenant_api.list_accessible_organizations()
        if not result.ok or result.data is None:
            return ()
        return tuple(self._serialize(o) for o in result.data)

    def get_active_organization_id(self) -> str:
        if self._tenant_api is None:
            return ""
        result = self._tenant_api.get_active_organization()
        if result.ok and result.data is not None:
            return result.data.id
        return ""

    def switch_to_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._tenant_api is None:
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    code="TENANT_API_NOT_CONNECTED",
                    message="Organization switching is not available.",
                    category="preview",
                ),
            )
        return self._tenant_api.switch_to_organization(organization_id)

    @staticmethod
    def _serialize(o: OrganizationDto) -> OrganizationSwitcherItemViewModel:
        return OrganizationSwitcherItemViewModel(
            id=o.id,
            display_name=o.display_name,
            organization_code=o.organization_code,
            is_enabled=o.is_enabled,
        )


__all__ = ["OrganizationSwitcherItemViewModel", "OrganizationSwitcherPresenter"]
