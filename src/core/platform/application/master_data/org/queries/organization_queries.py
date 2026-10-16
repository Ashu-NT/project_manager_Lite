from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

import src.core.platform.application.master_data.org.mappers.organization as response_mapper
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationCalendarSummaryDto,
    OrganizationCatalogPageDto,
    OrganizationDto,
    OrganizationStatisticsDto,
)
from src.core.platform.application.master_data.org.organization_context import (
    require_current_tenant_id,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.domain.master_data.org import (
    Organization,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationDeactivated,
)

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )
    from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
        EmployeeHeadcountReader,
    )
    from src.core.platform.domain.history.audit.audit_entry import AuditEntry
    from src.core.platform.domain.security.auth.session import UserSessionContext

logger = logging.getLogger(__name__)

ORGANIZATION_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)
_DEFAULT_ORGANIZATION_PAGE_SIZE = 25

_ORGANIZATION_STATUS_AUDIT_SEVERITY: dict[str, str] = {
    "organization.activate": "medium",
    "organization.deactivate": "medium",
    "organization.archive": "high",
}
_ORGANIZATION_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "organization.activate": "Organization activated — {name}",
    "organization.deactivate": "Organization deactivated — {name}",
    "organization.archive": "Organization archived — {name}",
}
_ORGANIZATION_STATUS_EVENT_CLASS: dict[str, type] = {
    "organization.activate": OrganizationActivated,
    "organization.deactivate": OrganizationDeactivated,
    "organization.archive": OrganizationArchived,
}

@dataclass(frozen=True)
class OrganizationPage:
    items: list[Organization] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_ORGANIZATION_PAGE_SIZE


@dataclass(frozen=True)
class OrganizationStatistics:
    site_count: int = 0
    department_count: int = 0
    employee_count: int = 0
    document_count: int = 0


@dataclass(frozen=True)
class OrganizationCalendarSummary:
    """Read-only summary of the organization's one default calendar, for
    Organization Overview/Inspector. has_calendar False means the migration
    invariant is somehow unmet -- the UI must show an empty state, not crash."""

    has_calendar: bool = False
    calendar_id: str = ""
    calendar_name: str = ""
    timezone: str = ""
    locale: str | None = None
    working_weekdays: tuple[int, ...] = ()
    holiday_count: int = 0


class OrganizationQueryHandler:
    """Organization reads for the active tenant: lists, the page, statistics,
    calendar summary, recent activity and count."""

    def __init__(
        self,
        *,
        session: Session,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None,
        enterprise_audit_service: EnterpriseAuditService | None,
        overview_rollup_reader: PlatformOverviewRollupReader | None,
        employee_headcount_reader: EmployeeHeadcountReader | None,
    ) -> None:
        self._session = session
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._overview_rollup_reader = overview_rollup_reader
        self._employee_headcount_reader = employee_headcount_reader

    def require_current_tenant_id(self, *, operation_label: str) -> str:
        """Public accessor for the tenant-resolution guard other Organization methods use internally."""
        return require_current_tenant_id(self._user_session, operation_label=operation_label)

    def list_organizations(self, *, status: str | None = None) -> list[OrganizationDto]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="list organizations")
        result = self._organization_repo.list_for_tenant(tenant_id, status=status)
        # This service's session is shared/long-lived (not a per-call
        # UnitOfWork session) -- a read-only call still opens an implicit
        # SQLite transaction on first use and never closes it on its own.
        # Left open, it blocks WAL checkpointing indefinitely and eventually
        # causes unrelated writers to fail with "database is locked". This
        # commit has no data to persist; it only ends that transaction.
        self._session.commit()
        return [response_mapper.serialize_organization(row) for row in (result)]

    def list_organizations_page(
        self,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_ORGANIZATION_PAGE_SIZE,
        search: str | None = None,
        status: str | None = None,
    ) -> OrganizationCatalogPageDto:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="list organizations")
        normalized_page = max(1, page)
        normalized_page_size = page_size if page_size in ORGANIZATION_PAGE_SIZE_OPTIONS else _DEFAULT_ORGANIZATION_PAGE_SIZE
        items, total, filtered_total = self._organization_repo.list_page_for_tenant(
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            status=status,
        )
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        return response_mapper.serialize_organization_page(OrganizationPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        ))

    def get_organization_statistics(self, organization_id: str) -> OrganizationStatisticsDto:
        """Composed real counts for one organization -- one aggregate query
        per entity via the existing overview/headcount read models, never a
        row-level fetch-and-count. Scoped to the given `organization_id`
        explicitly (not the caller's active organization), since Organization
        Detail may be showing an organization the user hasn't switched to."""
        require_permission(self._user_session, "settings.manage", operation_label="view organization statistics")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="view organization statistics")
        if self._overview_rollup_reader is None:
            return response_mapper.serialize_organization_statistics(OrganizationStatistics())
        site_summary = self._overview_rollup_reader.get_site_summary(
            organization_id=organization_id, tenant_id=tenant_id
        )
        department_summary = self._overview_rollup_reader.get_department_summary(
            organization_id=organization_id, tenant_id=tenant_id
        )
        document_summary = self._overview_rollup_reader.get_document_summary(
            organization_id=organization_id, tenant_id=tenant_id
        )
        employee_count = 0
        if self._employee_headcount_reader is not None:
            employee_count = self._employee_headcount_reader.get_summary(
                tenant_id=tenant_id, organization_id=organization_id
            ).total
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        return response_mapper.serialize_organization_statistics(OrganizationStatistics(
            site_count=site_summary.total,
            department_count=department_summary.total,
            employee_count=employee_count,
            document_count=document_summary.total,
        ))

    def get_organization_calendar_summary(self, organization_id: str) -> OrganizationCalendarSummaryDto:
        """Scoped to the given organization_id explicitly, matching
        get_organization_statistics() above -- Organization Overview may be
        showing an organization the caller hasn't switched to."""
        require_permission(self._user_session, "settings.manage", operation_label="view organization calendar")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="view organization calendar")
        if self._overview_rollup_reader is None:
            return response_mapper.serialize_organization_calendar_summary(OrganizationCalendarSummary())
        summary = self._overview_rollup_reader.get_calendar_summary(
            organization_id=organization_id, tenant_id=tenant_id
        )
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        if not summary.calendar_id:
            return response_mapper.serialize_organization_calendar_summary(OrganizationCalendarSummary())
        return response_mapper.serialize_organization_calendar_summary(OrganizationCalendarSummary(
            has_calendar=True,
            calendar_id=summary.calendar_id,
            calendar_name=summary.calendar_name,
            timezone=summary.timezone,
            locale=summary.locale,
            working_weekdays=summary.working_weekdays,
            holiday_count=summary.holiday_count,
        ))

    def get_organization_recent_activity(
        self, organization_id: str, *, limit: int = 5
    ) -> list[AuditEntry]:
        require_permission(self._user_session, "settings.manage", operation_label="view organization activity")
        require_current_tenant_id(self._user_session, operation_label="view organization activity")
        if self._enterprise_audit_service is None:
            return []
        result = self._enterprise_audit_service.list_recent_for_organization_id(
            organization_id, limit=limit
        )
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        return result

    def get_organization_count(self) -> int:
        require_permission(self._user_session, "settings.manage", operation_label="view organization count")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="view organization count")
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        result = self._overview_rollup_reader.get_organization_count(tenant_id=tenant_id)
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        return result


__all__ = ["ORGANIZATION_PAGE_SIZE_OPTIONS", "OrganizationCalendarSummary", "OrganizationPage", "OrganizationQueryHandler", "OrganizationStatistics"]
