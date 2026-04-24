from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    PlatformSiteDesktopApi,
    SiteCreateCommand,
    SiteDto,
    SiteUpdateCommand,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.ui_qml.platform.presenters.support import (
    bool_value,
    int_value,
    preview_error_result,
    string_value,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformSiteCatalogPresenter:
    def __init__(
        self,
        *,
        site_api: PlatformSiteDesktopApi | None = None,
    ) -> None:
        self._site_api = site_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._site_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle="Shared site records appear here once the platform site API is connected.",
                empty_state="Platform site API is not connected in this QML preview.",
            )

        context_result = self._site_api.get_context()
        sites_result = self._site_api.list_sites(active_only=None)
        if not sites_result.ok or sites_result.data is None:
            message = sites_result.error.message if sites_result.error is not None else "Unable to load sites."
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle=message,
                empty_state=message,
            )

        context_label = (
            context_result.data.display_name
            if context_result.ok and context_result.data is not None
            else "Context unavailable"
        )
        return PlatformWorkspaceActionListViewModel(
            title="Sites",
            subtitle=f"Shared site records for {context_label}.",
            empty_state="No sites are available yet.",
            items=tuple(self._serialize_site(row) for row in sites_result.data),
        )

    def create_site(self, payload: dict[str, Any]) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.create_site(
            SiteCreateCommand(
                site_code=string_value(payload, "siteCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                city=string_value(payload, "city"),
                country=string_value(payload, "country"),
                timezone_name=string_value(payload, "timezoneName"),
                currency_code=string_value(payload, "currencyCode").upper(),
                site_type=string_value(payload, "siteType"),
                status=string_value(payload, "status"),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
            )
        )

    def update_site(self, payload: dict[str, Any]) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.update_site(
            SiteUpdateCommand(
                site_id=string_value(payload, "siteId"),
                site_code=string_value(payload, "siteCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                city=string_value(payload, "city"),
                country=string_value(payload, "country"),
                timezone_name=string_value(payload, "timezoneName"),
                currency_code=string_value(payload, "currencyCode").upper(),
                site_type=string_value(payload, "siteType"),
                status=string_value(payload, "status"),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def toggle_site_active(
        self,
        *,
        site_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.update_site(
            SiteUpdateCommand(
                site_id=site_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    @staticmethod
    def _serialize_site(row: SiteDto) -> PlatformWorkspaceActionItemViewModel:
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.site_code} | {row.city or '-'} | {row.country or '-'}",
            supporting_text=f"{row.site_type or 'Site'} | Runtime status: {row.status or '-'}",
            meta_text=f"Timezone {row.timezone or '-'} | Currency {row.currency_code or '-'}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "siteId": row.id,
                "siteCode": row.site_code,
                "name": row.name,
                "description": row.description,
                "city": row.city,
                "country": row.country,
                "timezoneName": row.timezone,
                "currencyCode": row.currency_code,
                "siteType": row.site_type,
                "status": row.status,
                "notes": row.notes,
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformSiteCatalogPresenter"]
