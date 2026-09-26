from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.core.platform.access.authorization import (
    filter_scope_rows,
    require_scope_permission,
)
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    PlatformOverviewRollupReader,
    SiteRollupSummary,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.contract.uow.site_unit_of_work import SiteUnitOfWorkFactory
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.org.support import normalize_code
from src.core.platform.domain.master_data.site import Site
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

from . import site_commands as _cmd
from .site_context import active_organization
from .site_utils import normalize_optional_text

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )
    from src.core.platform.domain.security.auth.session import UserSessionContext


_DEFAULT_SITE_PAGE_SIZE = 25
SITE_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class SitePage:
    items: list[Site] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_SITE_PAGE_SIZE


class SiteService:
    def __init__(
        self,
        session: Session,
        site_repo: SiteRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
        uow_factory: SiteUnitOfWorkFactory,
        clock: Clock,
    ):
        self._session = session
        self._site_repo = site_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._uow_factory = uow_factory
        self._clock = clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def list_sites(self, *, active_only: bool | None = None) -> list[Site]:
        self._require_site_read_access("list sites")
        organization = self._active_organization()
        rows = self._site_repo.list_for_organization(organization.id, active_only=active_only)
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="site",
            permission_code="site.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_sites(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Site]:
        self._require_site_read_access("search sites")
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_sites(active_only=active_only)
        if not normalized_search:
            return rows
        return [
            site
            for site in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        site.site_code,
                        site.name,
                        site.city,
                        site.country,
                        site.site_type,
                        site.status,
                    ],
                )
            ).lower()
        ]

    def list_sites_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_SITE_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
    ) -> SitePage:
        """Tenant-scoped read for ANY organization in the caller's tenant --
        unlike list_sites()/search_sites(), not limited to the session's
        active organization. For Organization Detail's Sites tab, where an
        admin may be viewing an organization they haven't switched into.

        Read-only: never used by create/update/delete, which keep using
        self._active_organization() (the existing, unchanged domain rule).
        Never gates on the organization's own lifecycle status -- inactive
        and archived organizations' site history remains readable here.
        """
        self._require_site_read_access("list sites")
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Tenant context is required to list sites.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list sites for organization"
        )
        target_organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if target_organization is None:
            raise NotFoundError(
                "Organization not found in the current tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        normalized_page = max(1, page)
        normalized_page_size = page_size if page_size in SITE_PAGE_SIZE_OPTIONS else _DEFAULT_SITE_PAGE_SIZE
        items, total, filtered_total = self._site_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            active_only=active_only,
        )
        items = filter_scope_rows(
            items,
            self._user_session,
            scope_type="site",
            permission_code="site.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )
        return SitePage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

    def get_site(self, site_id: str) -> Site:
        self._require_site_read_access("view site")
        organization = self._active_organization()
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "site",
            site.id,
            "site.read",
            operation_label="view site",
        )
        return site

    def find_site_by_code(self, site_code: str) -> Site | None:
        self._require_site_read_access("resolve site")
        normalized_code = normalize_code(site_code, label="Site code")
        return self._site_repo.get_by_code(self._active_organization().id, normalized_code)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view site context")
        return self._active_organization()

    def create_site(
        self,
        *,
        site_code: str,
        name: str | None = None,
        display_name: str | None = None,
        description: str = "",
        country: str = "",
        region: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        timezone_name: str | None = None,
        currency_code: str | None = None,
        site_type: str = "",
        default_calendar_id: str = "",
        default_language: str = "",
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        notes: str = "",
    ) -> Site:
        return _cmd.create_site(
            self,
            site_code=site_code,
            name=name,
            display_name=display_name,
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone_name=timezone_name,
            currency_code=currency_code,
            site_type=site_type,
            default_calendar_id=default_calendar_id,
            default_language=default_language,
            opened_at=opened_at,
            closed_at=closed_at,
            notes=notes,
        )

    def update_site(
        self,
        site_id: str,
        *,
        site_code: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        country: str | None = None,
        region: str | None = None,
        city: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        postal_code: str | None = None,
        timezone_name: str | None = None,
        currency_code: str | None = None,
        site_type: str | None = None,
        default_calendar_id: str | None = None,
        default_language: str | None = None,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Site:
        return _cmd.update_site(
            self,
            site_id,
            site_code=site_code,
            name=name,
            display_name=display_name,
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone_name=timezone_name,
            currency_code=currency_code,
            site_type=site_type,
            default_calendar_id=default_calendar_id,
            default_language=default_language,
            opened_at=opened_at,
            closed_at=closed_at,
            notes=notes,
            expected_version=expected_version,
        )

    def activate_site(self, site_id: str) -> Site:
        return _cmd.activate_site(self, site_id)

    def deactivate_site(self, site_id: str) -> Site:
        return _cmd.deactivate_site(self, site_id)

    def archive_site(self, site_id: str) -> Site:
        return _cmd.archive_site(self, site_id)

    def _active_organization(self) -> Organization:
        return active_organization(self)

    def _require_site_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "site.read"),
            operation_label=operation_label,
        )

    def get_site_rollup_summary(self) -> SiteRollupSummary:
        self._require_site_read_access("view site rollup summary")
        organization = self._active_organization()
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view site rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")

        engine = get_authorization_engine()
        allowed_site_ids: frozenset[str] | None = None
        if engine.is_scope_restricted(self._user_session, "site"):
            allowed_site_ids = frozenset(
                engine.scope_ids_for(self._user_session, "site", "site.read")
            )

        return self._overview_rollup_reader.get_site_summary(
            organization_id=organization.id,
            tenant_id=tenant_id,
            allowed_site_ids=allowed_site_ids,
        )


__all__ = ["SiteService"]
