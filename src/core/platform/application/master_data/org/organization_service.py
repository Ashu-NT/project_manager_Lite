from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
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
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.uow.organization_unit_of_work import (
    OrganizationUnitOfWorkFactory,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import PlatformOverviewRollupReader
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.org.events import (
    OrganizationCreated,
    OrganizationDisabled,
    OrganizationEnabled,
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

ORGANIZATION_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)
_DEFAULT_ORGANIZATION_PAGE_SIZE = 25


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
            is_enabled=True,
            tenant_id=bootstrap_tenant_id,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            uow.organizations.add(organization)
            uow.commit()

    # ------------------------------------------------------------------
    # Runtime read operations — all tenant-scoped, fail-fast.
    # ------------------------------------------------------------------

    def list_organizations(self, *, enabled_only: bool | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
        result = self._organization_repo.list_for_tenant(tenant_id, enabled_only=enabled_only)
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
        enabled_only: bool | None = None,
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
            enabled_only=enabled_only,
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
        is_enabled: bool = True,
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
                is_enabled=is_enabled,
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
        is_enabled: bool | None = None,
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
                is_enabled=organization.is_enabled if is_enabled is None else is_enabled,
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
            availability_changed = candidate.is_enabled != organization.is_enabled
            if not profile_changed and not availability_changed:
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

                # A pure availability transition (no other field changed) gets its
                # own distinct action so the curated Organization Activity feed can
                # tell "deactivated" apart from an ordinary profile edit; a combined
                # change reports as the more complete "update".
                if availability_changed and not profile_changed:
                    audit_action = "organization.enable" if candidate.is_enabled else "organization.disable"
                else:
                    audit_action = "organization.update"
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
                    category="PRIVILEGED_OPERATION" if audit_action != "organization.update" else "MASTER_DATA",
                    severity="low",
                    changed_fields=(
                        {"is_enabled": {"before": str(organization.is_enabled), "after": str(candidate.is_enabled)}}
                        if availability_changed
                        else None
                    ),
                    after_data={
                        "organization_code": candidate.organization_code,
                        "display_name": candidate.display_name,
                        "timezone_name": candidate.timezone_name,
                        "base_currency": candidate.base_currency,
                        "is_enabled": candidate.is_enabled,
                        "legal_name": candidate.legal_name,
                        "registration_number": candidate.registration_number,
                        "country_code": candidate.country_code,
                        "email": candidate.email,
                    },
                    metadata={"action": audit_action},
                    commit=False,
                    fail_closed=True,
                )
                _ORG_ACTIVITY_MESSAGE = {
                    "organization.update": f"Organization updated — {candidate.display_name}",
                    "organization.enable": f"Organization enabled — {candidate.display_name}",
                    "organization.disable": f"Organization deactivated — {candidate.display_name}",
                }
                record_activity(
                    uow,
                    action=audit_action,
                    entity_type="organization",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=candidate.id,
                    message=_ORG_ACTIVITY_MESSAGE[audit_action],
                    icon="organization",
                    type="warning" if audit_action == "organization.disable" else "info",
                    commit=False,
                )
                occurred_at = self._clock.now()
                if profile_changed:
                    uow.record_event(
                        OrganizationProfileUpdated(
                            tenant_id=tenant_id,
                            organization_id=candidate.id,
                            occurred_at=occurred_at,
                        )
                    )
                if availability_changed:
                    availability_event_cls = (
                        OrganizationEnabled if candidate.is_enabled else OrganizationDisabled
                    )
                    uow.record_event(
                        availability_event_cls(
                            tenant_id=tenant_id,
                            organization_id=candidate.id,
                            occurred_at=occurred_at,
                        )
                    )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc

        if (
            availability_changed
            and not candidate.is_enabled
            and self._user_session is not None
            and self._user_session.active_organization_id() == candidate.id
        ):
            # Don't leave the session pointed at an organization it just disabled.
            self._user_session.set_active_organization_id(None)
        return candidate

    def enable_organization(self, organization_id: str) -> Organization:
        return self._set_organization_enabled(organization_id, is_enabled=True, action="organization.enable")

    def disable_organization(self, organization_id: str) -> Organization:
        return self._set_organization_enabled(organization_id, is_enabled=False, action="organization.disable")

    def _set_organization_enabled(
        self, organization_id: str, *, is_enabled: bool, action: str
    ) -> Organization:
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization availability"
        )
        tenant_id = self._require_current_tenant_id(operation_label="change organization availability")
        with self._uow_factory.create(context=self._new_context()) as uow:
            organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            candidate = self._apply_organization_enabled(
                uow, organization, tenant_id=tenant_id, is_enabled=is_enabled, action=action
            )
            uow.commit()
        self._clear_active_organization_if_disabled(candidate, is_enabled)
        return candidate

    def bulk_set_organization_enabled(
        self, organization_ids: Sequence[str], *, is_enabled: bool
    ) -> list[Organization]:
        """Same per-record work as enable_organization()/disable_organization() (own
        audit entry + activity entry + domain event per organization -- that's the
        audit trail's actual granularity, not something a single bulk SQL statement
        could replace), but all of it runs inside ONE UnitOfWork/commit instead of
        one per organization. For N selected rows this turns N SQLite write
        transactions (N fsyncs, N lock acquisitions) into 1, which is the dominant
        cost at any real bulk-selection size -- not the row updates themselves."""
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization availability"
        )
        tenant_id = self._require_current_tenant_id(operation_label="change organization availability")
        action = "organization.enable" if is_enabled else "organization.disable"
        results: list[Organization] = []
        with self._uow_factory.create(context=self._new_context()) as uow:
            for organization_id in organization_ids:
                organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
                if organization is None:
                    raise NotFoundError(
                        f"Organization not found: {organization_id}", code="ORGANIZATION_NOT_FOUND"
                    )
                results.append(
                    self._apply_organization_enabled(
                        uow, organization, tenant_id=tenant_id, is_enabled=is_enabled, action=action
                    )
                )
            uow.commit()
        for candidate in results:
            self._clear_active_organization_if_disabled(candidate, is_enabled)
        return results

    def _apply_organization_enabled(
        self, uow, organization: Organization, *, tenant_id: str, is_enabled: bool, action: str
    ) -> Organization:
        """Mutates one organization's availability inside an already-open uow
        (no commit) -- the single unit of work shared by the single-record and
        bulk paths above."""
        if organization.is_enabled == is_enabled:
            # No-op: a state-transition event must represent an actual transition.
            return organization
        candidate = replace(organization, is_enabled=is_enabled, tenant_id=tenant_id)
        uow.organizations.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="organization",
            entity_id=candidate.id,
            organization_id=candidate.id,
            module="platform",
            category="PRIVILEGED_OPERATION",
            severity="medium",
            changed_fields={"is_enabled": {"before": str(organization.is_enabled), "after": str(candidate.is_enabled)}},
            after_data={
                "organization_code": candidate.organization_code,
                "display_name": candidate.display_name,
                "is_enabled": candidate.is_enabled,
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
            message=(
                f"Organization enabled — {candidate.display_name}"
                if is_enabled
                else f"Organization deactivated — {candidate.display_name}"
            ),
            icon="organization",
            type="info" if is_enabled else "warning",
            commit=False,
        )
        availability_event_cls = OrganizationEnabled if is_enabled else OrganizationDisabled
        uow.record_event(
            availability_event_cls(
                tenant_id=tenant_id,
                organization_id=candidate.id,
                occurred_at=self._clock.now(),
            )
        )
        return candidate

    def _clear_active_organization_if_disabled(self, candidate: Organization, is_enabled: bool) -> None:
        if (
            not is_enabled
            and self._user_session is not None
            and self._user_session.active_organization_id() == candidate.id
        ):
            # Don't leave the session pointed at an organization it just disabled.
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
        is_enabled: bool,
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
            is_enabled=is_enabled,
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
                "is_enabled": organization.is_enabled,
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
