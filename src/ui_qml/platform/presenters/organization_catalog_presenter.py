from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
    PlatformRuntimeDesktopApi,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.ui_qml.platform.presenters.support import (
    bool_value,
    int_value,
    option_item,
    preview_error_result,
    string_value,
    tuple_of_strings,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformOrganizationCatalogPresenter:
    def __init__(
        self,
        *,
        runtime_api: PlatformRuntimeDesktopApi | None = None,
    ) -> None:
        self._runtime_api = runtime_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._runtime_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Organizations",
                subtitle="Organization records appear here once the platform runtime API is connected.",
                empty_state="Platform runtime API is not connected in this QML preview.",
            )

        result = self._runtime_api.list_organizations(active_only=None)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load organizations."
            return PlatformWorkspaceActionListViewModel(
                title="Organizations",
                subtitle=message,
                empty_state=message,
            )

        active_name = next((row.display_name for row in result.data if row.is_active), "No active organization")
        return PlatformWorkspaceActionListViewModel(
            title="Organizations",
            subtitle=f"Install profiles and hosting boundaries. Active: {active_name}.",
            empty_state="No organizations are available yet.",
            items=tuple(self._serialize_organization(row) for row in result.data),
        )

    def build_module_options(self) -> tuple[dict[str, str], ...]:
        if self._runtime_api is None:
            return ()
        result = self._runtime_api.list_modules()
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(
                label=module.label,
                value=module.code,
                supporting_text=module.description,
            )
            for module in result.data
        )

    def create_organization(self, payload: dict[str, Any]) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.provision_organization(
            OrganizationProvisionCommand(
                organization_code=string_value(payload, "organizationCode"),
                display_name=string_value(payload, "displayName"),
                timezone_name=string_value(payload, "timezoneName", default="UTC"),
                base_currency=string_value(payload, "baseCurrency", default="USD").upper(),
                is_active=bool_value(payload, "isActive", default=True),
                initial_module_codes=tuple_of_strings(payload, "initialModuleCodes"),
            )
        )

    def update_organization(self, payload: dict[str, Any]) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.update_organization(
            OrganizationUpdateCommand(
                organization_id=string_value(payload, "organizationId"),
                organization_code=string_value(payload, "organizationCode"),
                display_name=string_value(payload, "displayName"),
                timezone_name=string_value(payload, "timezoneName", default="UTC"),
                base_currency=string_value(payload, "baseCurrency", default="USD").upper(),
                is_active=bool_value(payload, "isActive", default=True),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def set_active_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        if self._runtime_api is None:
            return preview_error_result("Platform runtime API is not connected in this QML preview.")
        return self._runtime_api.set_active_organization(organization_id)

    @staticmethod
    def _serialize_organization(row: OrganizationDto) -> PlatformWorkspaceActionItemViewModel:
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.organization_code} | {row.timezone_name}",
            supporting_text=f"Base currency: {row.base_currency}",
            meta_text=f"Version {row.version}",
            can_primary_action=True,
            can_secondary_action=not row.is_active,
            state={
                "id": row.id,
                "organizationId": row.id,
                "organizationCode": row.organization_code,
                "displayName": row.display_name,
                "timezoneName": row.timezone_name,
                "baseCurrency": row.base_currency,
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformOrganizationCatalogPresenter"]
