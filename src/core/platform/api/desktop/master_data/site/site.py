from __future__ import annotations

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.master_data.site.models.site import (
    SiteDto,
    SitePageDto,
    SiteRollupSummaryDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.master_data.site.dto import (
    SiteCreateCommand,
    SiteUpdateCommand,
)


class PlatformSiteDesktopApi:
    """Desktop-facing adapter for platform site master data."""

    def __init__(
        self,
        *,
        site_commands: SiteCommandHandler,
        site_query: SiteQueryHandler,
    ) -> None:
        self._site_commands = site_commands
        self._site_query = site_query

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._site_query.get_context_organization())
        )

    def get_site_rollup_summary(self) -> DesktopApiResult[SiteRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_rollup_summary(
                self._site_query.get_site_rollup_summary()
            )
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[SiteDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_site(site)
                for site in self._site_query.list_sites(active_only=active_only)
            )
        )

    def list_sites_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
    ) -> DesktopApiResult[SitePageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site_page(
                self._site_query.list_sites_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                )
            )
        )

    def create_site(self, command: SiteCreateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(
                self._site_commands.create_site(command)
            )
        )

    def update_site(self, command: SiteUpdateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(
                self._site_commands.update_site(command)
            )
        )

    def activate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(self._site_commands.activate_site(site_id))
        )

    def deactivate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(self._site_commands.deactivate_site(site_id))
        )

    def archive_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(self._site_commands.archive_site(site_id))
        )

    def _serialize_site_page(self, page) -> SitePageDto:
        return SitePageDto(
            items=tuple(self._serialize_site(site) for site in page.items),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
        )

    @staticmethod
    def _serialize_rollup_summary(summary) -> SiteRollupSummaryDto:
        return SiteRollupSummaryDto(
            total=summary.total,
            active=summary.active,
            sample_names=summary.sample_names,
        )

    @staticmethod
    def _serialize_site(site) -> SiteDto:
        return SiteDto(
            id=site.id,
            organization_id=site.organization_id,
            site_code=site.site_code,
            name=site.name,
            description=site.description,
            country=site.country,
            region=site.region,
            city=site.city,
            address_line_1=site.address_line_1,
            address_line_2=site.address_line_2,
            postal_code=site.postal_code,
            timezone=site.timezone,
            currency_code=site.currency_code,
            site_type=site.site_type,
            status=site.status,
            default_calendar_id=site.default_calendar_id,
            default_language=site.default_language,
            is_active=site.is_active,
            notes=site.notes,
            version=site.version,
            opened_at=site.opened_at,
            closed_at=site.closed_at,
            created_at=site.created_at,
            updated_at=site.updated_at,
        )


__all__ = ["PlatformSiteDesktopApi"]
