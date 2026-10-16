from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.master_data.site.dto.commands.site import (
    SiteCreateCommand,
    SiteUpdateCommand,
)
from src.core.platform.application.master_data.site.dto.responses.site import (
    SiteDto,
    SitePageDto,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    SiteRollupSummary,
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
            lambda: self._site_query.get_context_organization()
        )

    def get_site_rollup_summary(self) -> DesktopApiResult[SiteRollupSummary]:
        return execute_desktop_operation(
            lambda: self._site_query.get_site_rollup_summary()
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[SiteDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                site
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
            lambda: self._site_query.list_sites_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                )
        )

    def create_site(self, command: SiteCreateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._site_commands.create_site(command)
        )

    def update_site(self, command: SiteUpdateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._site_commands.update_site(command)
        )

    def activate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._site_commands.activate_site(site_id)
        )

    def deactivate_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._site_commands.deactivate_site(site_id)
        )

    def archive_site(self, site_id: str) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._site_commands.archive_site(site_id)
        )





__all__ = ["PlatformSiteDesktopApi"]
