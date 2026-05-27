from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation, serialize_organization
from src.api.desktop.platform.models import (
    DesktopApiResult,
    OrganizationDto,
    SiteCreateCommand,
    SiteDto,
    SiteUpdateCommand,
)
from src.core.platform.org import SiteService


class PlatformSiteDesktopApi:
    """Desktop-facing adapter for platform site master data."""

    def __init__(self, *, site_service: SiteService) -> None:
        self._site_service = site_service

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._site_service.get_context_organization())
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[SiteDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_site(site)
                for site in self._site_service.list_sites(active_only=active_only)
            )
        )

    def create_site(self, command: SiteCreateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(
                self._site_service.create_site(
                    site_code=command.site_code,
                    name=command.name,
                    description=command.description,
                    country=command.country,
                    region=command.region,
                    city=command.city,
                    address_line_1=command.address_line_1,
                    address_line_2=command.address_line_2,
                    postal_code=command.postal_code,
                    timezone_name=command.timezone_name,
                    currency_code=command.currency_code,
                    site_type=command.site_type,
                    status=command.status,
                    default_calendar_id=command.default_calendar_id,
                    default_language=command.default_language,
                    is_active=command.is_active,
                    notes=command.notes,
                )
            )
        )

    def update_site(self, command: SiteUpdateCommand) -> DesktopApiResult[SiteDto]:
        return execute_desktop_operation(
            lambda: self._serialize_site(
                self._site_service.update_site(
                    command.site_id,
                    site_code=command.site_code,
                    name=command.name,
                    description=command.description,
                    country=command.country,
                    region=command.region,
                    city=command.city,
                    address_line_1=command.address_line_1,
                    address_line_2=command.address_line_2,
                    postal_code=command.postal_code,
                    timezone_name=command.timezone_name,
                    currency_code=command.currency_code,
                    site_type=command.site_type,
                    status=command.status,
                    default_calendar_id=command.default_calendar_id,
                    default_language=command.default_language,
                    is_active=command.is_active,
                    notes=command.notes,
                    expected_version=command.expected_version,
                )
            )
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
        )


__all__ = ["PlatformSiteDesktopApi"]
