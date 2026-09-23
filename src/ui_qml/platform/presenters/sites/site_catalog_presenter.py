from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.master_data.site.models.site import (
    SiteCreateCommand,
    SiteDto,
    SiteUpdateCommand,
)
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
    int_value,
    preview_error_result,
    string_value,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)

# Site lifecycle is now the same guarded 3-state active/inactive/archived
# model as Organization -- see SITE_STATUS_* (domain) and
# activate_site/deactivate_site/archive_site (service/API/presenter below).
_SITE_STATUS_TONE = {"active": "success", "inactive": "neutral", "archived": "neutral"}


def _site_status_label(status: str) -> dict[str, str]:
    return {"label": status.capitalize(), "tone": _SITE_STATUS_TONE.get(status, "neutral")}


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
            items=tuple(
                self._serialize_site(row, organization_name=context_label)
                for row in sites_result.data
            ),
        )

    def build_catalog_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Server-side paginated Sites page for the primary Platform > Sites
        destination, scoped to the caller's currently active organization --
        the ambient-context counterpart to build_catalog_page_for_organization
        below (Organization Detail's explicit-organization_id variant)."""
        if self._site_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle="Sites appear here once the platform site API is connected.",
                empty_state="Platform site API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )
        context_result = self._site_api.get_context()
        if not context_result.ok or context_result.data is None:
            message = context_result.error.message if context_result.error is not None else "Unable to load sites."
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )
        return self._build_catalog_page_for_organization(
            context_result.data.id,
            organization_name=context_result.data.display_name,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
        )

    def build_catalog_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        """Tenant-scoped (not active-organization-scoped) paginated Sites
        page for Organization Detail's Sites tab -- works regardless of
        which organization is currently active in the caller's session."""
        return self._build_catalog_page_for_organization(
            organization_id,
            organization_name="",
            page=page,
            page_size=page_size,
            search=search,
            status=status,
        )

    def _build_catalog_page_for_organization(
        self,
        organization_id: str,
        *,
        organization_name: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> PlatformWorkspaceActionListViewModel:
        if self._site_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle="Sites appear here once the platform site API is connected.",
                empty_state="Platform site API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )

        active_only: bool | None
        if status == "active":
            active_only = True
        elif status == "inactive":
            active_only = False
        else:
            active_only = None

        result = self._site_api.list_sites_page_for_organization(
            organization_id,
            page=page,
            page_size=page_size,
            search=search.strip(),
            active_only=active_only,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load sites."
            return PlatformWorkspaceActionListViewModel(
                title="Sites",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        site_page = result.data
        return PlatformWorkspaceActionListViewModel(
            title="Sites",
            subtitle="Operational sites for this organization.",
            empty_state="No sites yet. Add the first operational site for this organization.",
            no_results_state="No sites match your current filters.",
            items=tuple(self._serialize_site(row, organization_name=organization_name) for row in site_page.items),
            paginated=True,
            page=site_page.page,
            page_size=site_page.page_size,
            total_count=site_page.total,
            filtered_total=site_page.filtered_total,
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        """Suggest a unique site code (SITE-<NAME>-0001 / SITE-<YEAR>-0001)."""
        from src.core.platform.common.code_generation import CodeGenerator

        existing: set[str] = set()
        if self._site_api is not None:
            result = self._site_api.list_sites(active_only=None)
            if result.ok and result.data is not None:
                existing = {str(getattr(row, "site_code", "") or "").upper() for row in result.data}
        name = string_value(payload, "name")
        return CodeGenerator().generate(
            "site",
            exists=lambda code: code.upper() in existing,
            name=name or None,
            use_year=not bool(name),
        )

    def create_site(self, payload: dict[str, Any]) -> DesktopApiResult[SiteDto]:
        """Lifecycle is not settable from Create -- every new site starts
        ACTIVE (SiteCreateCommand's own default); status/isActive are never
        read from the payload here."""
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.create_site(
            SiteCreateCommand(
                site_code=string_value(payload, "siteCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                city=string_value(payload, "city"),
                region=string_value(payload, "region"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                country=string_value(payload, "country"),
                timezone_name=string_value(payload, "timezoneName"),
                currency_code=string_value(payload, "currencyCode").upper(),
                site_type=string_value(payload, "siteType"),
                notes=string_value(payload, "notes"),
            )
        )

    def update_site(self, payload: dict[str, Any]) -> DesktopApiResult[SiteDto]:
        """Pure profile update -- lifecycle is never settable from Edit; use
        activate_site/deactivate_site/archive_site below instead."""
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.update_site(
            SiteUpdateCommand(
                site_id=string_value(payload, "siteId"),
                site_code=string_value(payload, "siteCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                city=string_value(payload, "city"),
                region=string_value(payload, "region"),
                address_line_1=string_value(payload, "addressLine1"),
                address_line_2=string_value(payload, "addressLine2"),
                postal_code=string_value(payload, "postalCode"),
                country=string_value(payload, "country"),
                timezone_name=string_value(payload, "timezoneName"),
                currency_code=string_value(payload, "currencyCode").upper(),
                site_type=string_value(payload, "siteType"),
                notes=string_value(payload, "notes"),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def activate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.activate_site(site_id)

    def deactivate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.deactivate_site(site_id)

    def archive_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        if self._site_api is None:
            return preview_error_result("Platform site API is not connected in this QML preview.")
        return self._site_api.archive_site(site_id)

    @staticmethod
    def _serialize_site(
        row: SiteDto,
        *,
        organization_name: str,
    ) -> PlatformWorkspaceActionItemViewModel:
        location = ", ".join(part for part in (row.city, row.country) if part)
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.name,
            status_label=_site_status_label(row.status),
            subtitle=f"{row.site_code} | {row.city or '-'} | {row.country or '-'}",
            supporting_text=f"{row.site_type or 'Site'} | Runtime status: {row.status or '-'}",
            meta_text=f"Timezone {row.timezone or '-'} | Currency {row.currency_code or '-'}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "siteId": row.id,
                "organizationId": row.organization_id,
                "organizationName": organization_name,
                "siteCode": row.site_code,
                "name": row.name,
                "description": row.description,
                "city": row.city,
                "region": row.region,
                "addressLine1": row.address_line_1,
                "addressLine2": row.address_line_2,
                "postalCode": row.postal_code,
                "country": row.country,
                "location": location,
                "timezoneName": row.timezone,
                "currencyCode": row.currency_code,
                "siteType": row.site_type,
                "status": row.status,
                "isActive": row.is_active,
                "notes": row.notes,
                "version": row.version,
                "createdAt": row.created_at.isoformat() if row.created_at else "",
                "updatedAt": row.updated_at.isoformat() if row.updated_at else "",
            },
        )

__all__ = ["PlatformSiteCatalogPresenter"]
