from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.domain.time_management.calendar.enterprise_calendar import CalendarType
from src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar import (
    CalendarWorkingRuleORM,
    PlatformCalendarORM,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.uow.organization_unit_of_work import (
    OrganizationUnitOfWorkFactory,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import PlatformOverviewRollupReader
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import (
    ORGANIZATION_STATUS_ACTIVE,
    ORGANIZATION_STATUS_ARCHIVED,
    ORGANIZATION_STATUS_INACTIVE,
    Organization,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationCreated,
    OrganizationDeactivated,
    OrganizationProfileUpdated,
)
from src.core.platform.domain.master_data.org.support import (
    DEFAULT_ORGANIZATION_CODE,
    DEFAULT_ORGANIZATION_CURRENCY,
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_TIMEZONE,
)
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
        EmployeeHeadcountReader,
    )
    from src.core.platform.domain.history.audit.audit_entry import AuditEntry
    from src.core.platform.domain.security.auth.session import UserSessionContext
    from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService

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

# Mon-Fri 08:00-17:00 with a 60-minute break -- the same fresh-install
# default EnterpriseCalendarService.ensure_global_calendar() seeds when no
# legacy working_calendar data exists to migrate.
_DEFAULT_WORKING_WEEKDAYS = frozenset({0, 1, 2, 3, 4})


def _add_default_calendar_rows(session: Session, organization: Organization) -> None:
    """Every organization gets exactly one default (Global-tier) calendar,
    created in the SAME transaction as the organization itself -- the
    invariant is "an organization cannot exist without its required
    calendar", not "an organization gets one shortly after, best-effort".

    Written directly as ORM rows (not through PlatformCalendarRepository/
    CalendarWorkingRuleRepository) because those repositories are
    TenantScopedRepositorySupport-scoped to the CALLER's ACTIVE organization
    -- they silently redirect organization_id/tenant_id to the active
    scope regardless of what's passed in, which would write the calendar
    under the wrong organization for every organization created while a
    DIFFERENT one happens to be active (the normal case). This service
    already knows the exact, just-validated organization/tenant scope from
    `organization` itself, so that ambient scoping doesn't apply here.

    The client can edit this calendar afterward from the Calendars
    workspace -- this only guarantees it exists to begin with.
    """
    now = datetime.now(timezone.utc)
    calendar_id = f"global-{organization.id[:8]}"
    session.add(
        PlatformCalendarORM(
            id=calendar_id,
            tenant_id=organization.tenant_id,
            organization_id=organization.id,
            code="GLOBAL",
            name="Global Calendar",
            description="Organization-wide default working calendar.",
            calendar_type=CalendarType.GLOBAL.value,
            timezone="UTC",
            is_default=True,
            is_active=True,
            priority=0,
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    # Flush so the calendar row (and the organization row it -- and every
    # working rule row below -- has a foreign key to) physically exists
    # before the dependent inserts below are sent, regardless of how this
    # session's autoflush/dependency-sort settings are configured.
    session.flush()
    for weekday in range(7):
        is_working = weekday in _DEFAULT_WORKING_WEEKDAYS
        session.add(
            CalendarWorkingRuleORM(
                id=generate_id(),
                calendar_id=calendar_id,
                weekday=weekday,
                is_working_day=is_working,
                start_time=time(8, 0) if is_working else None,
                end_time=time(17, 0) if is_working else None,
                break_minutes=60 if is_working else 0,
                hours_override=8.0 if is_working else None,
                priority=0,
            )
        )


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


class OrganizationService:
    def __init__(
        self,
        session: Session,
        organization_repo: OrganizationRepository,
        *,
        uow_factory: OrganizationUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
        employee_headcount_reader: EmployeeHeadcountReader | None = None,
    ):
        self._session = session
        self._organization_repo = organization_repo
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._employee_headcount_reader = employee_headcount_reader

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    # ------------------------------------------------------------------
    # Tenant context — the single gateway for all runtime methods.
    # Raises TENANT_CONTEXT_REQUIRED immediately if no active tenant.
    # ------------------------------------------------------------------

    def _require_current_tenant_id(self, *, operation_label: str) -> str:
        if self._user_session is None:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = str(self._user_session.active_tenant_id() or "").strip()
        if not tenant_id:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_id

    def require_current_tenant_id(self, *, operation_label: str) -> str:
        """Public accessor for the tenant-resolution guard other Organization methods use internally."""
        return self._require_current_tenant_id(operation_label=operation_label)

    # ------------------------------------------------------------------
    # Bootstrap — runs before a tenant record exists in the system.
    # Uses unscoped list_all() only when no tenant context is present.
    # When a tenant context IS present (runtime re-call), scopes by it
    # so it never creates an untenanted organization at runtime.
    # ------------------------------------------------------------------

    def bootstrap_defaults(self) -> None:
        bootstrap_tenant_id = (
            str(self._user_session.active_tenant_id() or "").strip()
            if self._user_session is not None
            else ""
        ) or None

        if bootstrap_tenant_id:
            if self._organization_repo.list_for_tenant(bootstrap_tenant_id):
                return
        else:
            if self._organization_repo.list_all():
                return

        organization = Organization.create(
            organization_code=DEFAULT_ORGANIZATION_CODE,
            display_name=DEFAULT_ORGANIZATION_NAME,
            timezone_name=DEFAULT_ORGANIZATION_TIMEZONE,
            base_currency=DEFAULT_ORGANIZATION_CURRENCY,
            tenant_id=bootstrap_tenant_id,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            uow.organizations.add(organization)
            uow.commit()

    # ------------------------------------------------------------------
    # Runtime read operations — all tenant-scoped, fail-fast.
    # ------------------------------------------------------------------

    def list_organizations(self, *, status: str | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
        result = self._organization_repo.list_for_tenant(tenant_id, status=status)
        # This service's session is shared/long-lived (not a per-call
        # UnitOfWork session) -- a read-only call still opens an implicit
        # SQLite transaction on first use and never closes it on its own.
        # Left open, it blocks WAL checkpointing indefinitely and eventually
        # causes unrelated writers to fail with "database is locked". This
        # commit has no data to persist; it only ends that transaction.
        self._session.commit()
        return result

    def list_organizations_page(
        self,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_ORGANIZATION_PAGE_SIZE,
        search: str | None = None,
        status: str | None = None,
    ) -> OrganizationPage:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
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
        return OrganizationPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

    def get_organization_statistics(self, organization_id: str) -> OrganizationStatistics:
        """Composed real counts for one organization -- one aggregate query
        per entity via the existing overview/headcount read models, never a
        row-level fetch-and-count. Scoped to the given `organization_id`
        explicitly (not the caller's active organization), since Organization
        Detail may be showing an organization the user hasn't switched to."""
        require_permission(self._user_session, "settings.manage", operation_label="view organization statistics")
        tenant_id = self._require_current_tenant_id(operation_label="view organization statistics")
        if self._overview_rollup_reader is None:
            return OrganizationStatistics()
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
        return OrganizationStatistics(
            site_count=site_summary.total,
            department_count=department_summary.total,
            employee_count=employee_count,
            document_count=document_summary.total,
        )

    def get_organization_recent_activity(
        self, organization_id: str, *, limit: int = 5
    ) -> list[AuditEntry]:
        require_permission(self._user_session, "settings.manage", operation_label="view organization activity")
        self._require_current_tenant_id(operation_label="view organization activity")
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
        tenant_id = self._require_current_tenant_id(operation_label="view organization count")
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        result = self._overview_rollup_reader.get_organization_count(tenant_id=tenant_id)
        # See list_organizations() -- releases the implicit read transaction
        # on this shared session so it never blocks WAL checkpointing.
        self._session.commit()
        return result

    # ------------------------------------------------------------------
    # Runtime write operations — all tenant-scoped, fail-fast.
    # tenant_id is always re-pinned on the domain object before write
    # so the service layer is the authority, not the object's field.
    # ------------------------------------------------------------------

    def create_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str = DEFAULT_ORGANIZATION_TIMEZONE,
        base_currency: str = DEFAULT_ORGANIZATION_CURRENCY,
        legal_name: str = "",
        registration_number: str = "",
        tax_id: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        city: str = "",
        state_region: str = "",
        country_code: str = "",
        email: str = "",
        phone: str = "",
        website: str = "",
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="create organization")
        tenant_id = self._require_current_tenant_id(operation_label="create organization")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = self._create_organization_using(
                uow.organizations,
                uow,
                organization_code=organization_code,
                display_name=display_name,
                timezone_name=timezone_name,
                base_currency=base_currency,
                tenant_id=tenant_id,
                legal_name=legal_name,
                registration_number=registration_number,
                tax_id=tax_id,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                postal_code=postal_code,
                city=city,
                state_region=state_region,
                country_code=country_code,
                email=email,
                phone=phone,
                website=website,
            )
            _add_default_calendar_rows(uow.session, organization)
            try:
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        return organization

    def update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        expected_version: int | None = None,
        legal_name: str | None = None,
        registration_number: str | None = None,
        tax_id: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        postal_code: str | None = None,
        city: str | None = None,
        state_region: str | None = None,
        country_code: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        website: str | None = None,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = self._require_current_tenant_id(operation_label="update organization")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            if expected_version is not None and organization.version != expected_version:
                raise ConcurrencyError(
                    "Organization changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            candidate = replace(
                organization,
                organization_code=(
                    organization.organization_code
                    if organization_code is None
                    else organization_code
                ),
                display_name=organization.display_name if display_name is None else display_name,
                timezone_name=organization.timezone_name if timezone_name is None else timezone_name,
                base_currency=organization.base_currency if base_currency is None else base_currency,
                legal_name=organization.legal_name if legal_name is None else legal_name,
                registration_number=(
                    organization.registration_number if registration_number is None else registration_number
                ),
                tax_id=organization.tax_id if tax_id is None else tax_id,
                address_line_1=organization.address_line_1 if address_line_1 is None else address_line_1,
                address_line_2=organization.address_line_2 if address_line_2 is None else address_line_2,
                postal_code=organization.postal_code if postal_code is None else postal_code,
                city=organization.city if city is None else city,
                state_region=organization.state_region if state_region is None else state_region,
                country_code=organization.country_code if country_code is None else country_code,
                email=organization.email if email is None else email,
                phone=organization.phone if phone is None else phone,
                website=organization.website if website is None else website,
                tenant_id=tenant_id,
            )
            profile_changed = (
                candidate.organization_code != organization.organization_code
                or candidate.display_name != organization.display_name
                or candidate.timezone_name != organization.timezone_name
                or candidate.base_currency != organization.base_currency
                or candidate.legal_name != organization.legal_name
                or candidate.registration_number != organization.registration_number
                or candidate.tax_id != organization.tax_id
                or candidate.address_line_1 != organization.address_line_1
                or candidate.address_line_2 != organization.address_line_2
                or candidate.postal_code != organization.postal_code
                or candidate.city != organization.city
                or candidate.state_region != organization.state_region
                or candidate.country_code != organization.country_code
                or candidate.email != organization.email
                or candidate.phone != organization.phone
                or candidate.website != organization.website
            )
            if not profile_changed:
                # No-op: a state-transition event must represent an actual transition.
                return organization

            existing = uow.organizations.get_by_code_for_tenant(
                candidate.organization_code,
                tenant_id,
            )
            if existing is not None and existing.id != organization.id:
                raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
            try:
                uow.organizations.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    # Explicit, not left to the active-session fallback --
                    # this organization is not necessarily the caller's
                    # active one (Organization Detail can edit any org).
                    organization_id=candidate.id,
                    module="platform",
                    category="MASTER_DATA",
                    severity="low",
                    after_data={
                        "organization_code": candidate.organization_code,
                        "display_name": candidate.display_name,
                        "timezone_name": candidate.timezone_name,
                        "base_currency": candidate.base_currency,
                        "status": candidate.status,
                        "legal_name": candidate.legal_name,
                        "registration_number": candidate.registration_number,
                        "country_code": candidate.country_code,
                        "email": candidate.email,
                    },
                    metadata={"action": "organization.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="organization.update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=candidate.id,
                    message=f"Organization updated — {candidate.display_name}",
                    icon="organization",
                    type="info",
                    commit=False,
                )
                uow.record_event(
                    OrganizationProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        return candidate

    # Lifecycle transitions:
    #   active   -> inactive  (deactivate_organization)
    #   inactive -> active    (activate_organization)
    #   active   -> archived  (archive_organization)
    #   inactive -> archived  (archive_organization)
    #   archived -> anything  not allowed -- archived is terminal by default.

    def activate_organization(self, organization_id: str) -> Organization:
        return self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_ACTIVE, action="organization.activate"
        )

    def deactivate_organization(self, organization_id: str) -> Organization:
        return self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_INACTIVE, action="organization.deactivate"
        )

    def archive_organization(self, organization_id: str) -> Organization:
        return self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_ARCHIVED, action="organization.archive"
        )

    def _transition_organization_status(
        self, organization_id: str, *, new_status: str, action: str
    ) -> Organization:
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization status"
        )
        tenant_id = self._require_current_tenant_id(operation_label="change organization status")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            self._require_valid_organization_transition(organization, new_status)
            candidate = self._apply_organization_status(
                uow, organization, tenant_id=tenant_id, new_status=new_status, action=action
            )
            uow.commit()
        self._clear_active_organization_if_not_active(candidate)
        return candidate

    def bulk_activate_organizations(self, organization_ids: Sequence[str]) -> list[Organization]:
        return self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_ACTIVE, action="organization.activate"
        )

    def bulk_deactivate_organizations(self, organization_ids: Sequence[str]) -> list[Organization]:
        return self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_INACTIVE, action="organization.deactivate"
        )

    def bulk_archive_organizations(self, organization_ids: Sequence[str]) -> list[Organization]:
        return self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_ARCHIVED, action="organization.archive"
        )

    def _bulk_transition_organization_status(
        self, organization_ids: Sequence[str], *, new_status: str, action: str
    ) -> list[Organization]:
        """Same per-record work as the single-organization transition above (own
        audit entry + activity entry + domain event per organization -- that's the
        audit trail's actual granularity, not something a single bulk SQL statement
        could replace), but all of it runs inside ONE UnitOfWork/commit instead of
        one per organization. For N selected rows this turns N SQLite write
        transactions (N fsyncs, N lock acquisitions) into 1, which is the dominant
        cost at any real bulk-selection size -- not the row updates themselves."""
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization status"
        )
        tenant_id = self._require_current_tenant_id(operation_label="change organization status")
        results: list[Organization] = []
        with self._uow_factory.create(context=self._new_context()) as uow:
            for organization_id in organization_ids:
                organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
                if organization is None:
                    raise NotFoundError(
                        f"Organization not found: {organization_id}", code="ORGANIZATION_NOT_FOUND"
                    )
                self._require_valid_organization_transition(organization, new_status)
                results.append(
                    self._apply_organization_status(
                        uow, organization, tenant_id=tenant_id, new_status=new_status, action=action
                    )
                )
            uow.commit()
        for candidate in results:
            self._clear_active_organization_if_not_active(candidate)
        return results

    @staticmethod
    def _require_valid_organization_transition(organization: Organization, new_status: str) -> None:
        current = organization.status
        if current == new_status:
            raise BusinessRuleError(
                f"Organization is already {new_status}.",
                code=f"ORGANIZATION_ALREADY_{new_status.upper()}",
            )
        if current == ORGANIZATION_STATUS_ARCHIVED:
            raise BusinessRuleError(
                "Archived organizations cannot be reactivated or deactivated directly.",
                code="ORGANIZATION_ARCHIVED",
            )

    def _apply_organization_status(
        self, uow, organization: Organization, *, tenant_id: str, new_status: str, action: str
    ) -> Organization:
        """Mutates one organization's status inside an already-open uow (no
        commit) -- the single unit of work shared by the single-record and
        bulk paths above."""
        candidate = replace(organization, status=new_status, tenant_id=tenant_id)
        uow.organizations.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="organization",
            entity_id=candidate.id,
            organization_id=candidate.id,
            module="platform",
            category="PRIVILEGED_OPERATION",
            severity=_ORGANIZATION_STATUS_AUDIT_SEVERITY[action],
            changed_fields={"status": {"before": organization.status, "after": candidate.status}},
            after_data={
                "organization_code": candidate.organization_code,
                "display_name": candidate.display_name,
                "status": candidate.status,
            },
            metadata={"action": action},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action=action,
            entity_type="organization",
            entity_id=candidate.id,
            module="platform",
            organization_id=candidate.id,
            message=_ORGANIZATION_STATUS_ACTIVITY_MESSAGE[action].format(name=candidate.display_name),
            icon="organization",
            type="info" if action == "organization.activate" else "warning",
            commit=False,
        )
        uow.record_event(
            _ORGANIZATION_STATUS_EVENT_CLASS[action](
                tenant_id=tenant_id,
                organization_id=candidate.id,
                occurred_at=self._clock.now(),
            )
        )
        return candidate

    def _clear_active_organization_if_not_active(self, candidate: Organization) -> None:
        if (
            candidate.status != ORGANIZATION_STATUS_ACTIVE
            and self._user_session is not None
            and self._user_session.active_organization_id() == candidate.id
        ):
            # Don't leave the session pointed at an organization that just
            # stopped being active.
            self._user_session.set_active_organization_id(None)

    def bulk_update_organization_currency(
        self, organization_ids: Sequence[str], base_currency: str
    ) -> list[Organization]:
        return self._bulk_update_organization_field(
            organization_ids, field_name="base_currency", value=base_currency.strip().upper()
        )

    def bulk_update_organization_timezone(
        self, organization_ids: Sequence[str], timezone_name: str
    ) -> list[Organization]:
        return self._bulk_update_organization_field(
            organization_ids, field_name="timezone_name", value=timezone_name.strip()
        )

    def _bulk_update_organization_field(
        self, organization_ids: Sequence[str], *, field_name: str, value: str
    ) -> list[Organization]:
        """Narrow single-field bulk update (currency or timezone) -- deliberately
        not update_organization()'s full-record path, which needs the caller to
        already have every other field's current value in hand (the single-org
        edit form does; a bulk action across N rows never does). One UnitOfWork/
        commit for the whole selection, same reasoning as bulk_set_organization_
        enabled() above."""
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = self._require_current_tenant_id(operation_label="update organization")
        results: list[Organization] = []
        with self._uow_factory.create(context=self._new_context()) as uow:
            for organization_id in organization_ids:
                organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
                if organization is None:
                    raise NotFoundError(
                        f"Organization not found: {organization_id}", code="ORGANIZATION_NOT_FOUND"
                    )
                if getattr(organization, field_name) == value:
                    results.append(organization)
                    continue
                candidate = replace(organization, tenant_id=tenant_id, **{field_name: value})
                uow.organizations.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    organization_id=candidate.id,
                    module="platform",
                    category="MASTER_DATA",
                    severity="low",
                    changed_fields={field_name: {"before": getattr(organization, field_name), "after": value}},
                    metadata={"action": "organization.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="organization.update",
                    entity_type="organization",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=candidate.id,
                    message=f"Organization updated — {candidate.display_name}",
                    icon="organization",
                    type="info",
                    commit=False,
                )
                uow.record_event(
                    OrganizationProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                results.append(candidate)
            uow.commit()
        return results


    def _create_organization_using(
        self,
        organization_repo: OrganizationRepository,
        uow: object,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str,
        base_currency: str,
        tenant_id: str,
        legal_name: str = "",
        registration_number: str = "",
        tax_id: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        city: str = "",
        state_region: str = "",
        country_code: str = "",
        email: str = "",
        phone: str = "",
        website: str = "",
    ) -> Organization:
        organization = Organization.create(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            tenant_id=tenant_id,
            legal_name=legal_name,
            registration_number=registration_number,
            tax_id=tax_id,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            city=city,
            state_region=state_region,
            country_code=country_code,
            email=email,
            phone=phone,
            website=website,
        )
        if organization_repo.get_by_code_for_tenant(organization.organization_code, tenant_id) is not None:
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
        organization_repo.add(organization)
        # Flush so the new organization row exists before the audit/activity
        # entries below reference it via organization_id -- both would
        # otherwise land in the same flush batch with no ORM relationship()
        # to tell SQLAlchemy the FK must go second. Some callers (unit tests)
        # use a fully in-memory UnitOfWork fake with no real Session at all,
        # where this is a correct no-op.
        session = getattr(uow, "_session", None)
        if session is not None:
            session.flush()
        record_audit_entry(
            uow,
            operation="create",
            entity_type="organization",
            entity_id=organization.id,
            # The new organization's own id, not the caller's active org
            # context (which is a different organization entirely, if any).
            organization_id=organization.id,
            module="platform",
            category="MASTER_DATA",
            severity="low",
            after_data={
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "status": organization.status,
                "legal_name": organization.legal_name,
                "registration_number": organization.registration_number,
                "country_code": organization.country_code,
                "email": organization.email,
            },
            metadata={"action": "organization.create"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action="organization.create",
            entity_type="organization",
            entity_id=organization.id,
            module="platform",
            organization_id=organization.id,
            message=f"Organization created — {organization.display_name}",
            icon="organization",
            commit=False,
        )
        uow.record_event(
            OrganizationCreated(
                tenant_id=tenant_id,
                organization_id=organization.id,
                name=organization.display_name,
                code=organization.organization_code,
                occurred_at=self._clock.now(),
            )
        )
        return organization


__all__ = [
    "ORGANIZATION_PAGE_SIZE_OPTIONS",
    "OrganizationPage",
    "OrganizationService",
    "OrganizationStatistics",
]
