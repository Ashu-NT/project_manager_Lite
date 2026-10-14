from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.site.dto import (
    SiteCreateCommand,
    SiteUpdateCommand,
)
from src.core.platform.application.master_data.site.site_context import (
    active_organization,
)
from src.core.platform.application.master_data.site.site_utils import (
    normalize_optional_text,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.master_data.site import (
    SITE_STATUS_ACTIVE,
    SITE_STATUS_ARCHIVED,
    SITE_STATUS_INACTIVE,
    Site,
)
from src.core.platform.domain.master_data.site.events import (
    SiteActivated,
    SiteArchived,
    SiteCreated,
    SiteDeactivated,
    SiteProfileUpdated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

if TYPE_CHECKING:
    from src.core.platform.domain.master_data.org import Organization


def _event_tenant_id(organization: Organization) -> str:
    # Active-context organizations are tenant-scoped; the value is passed to
    # the domain events unchanged.
    return cast(str, organization.tenant_id)


_SITE_STATUS_AUDIT_SEVERITY: dict[str, str] = {
    "site.activate": "medium",
    "site.deactivate": "medium",
    "site.archive": "high",
}
_SITE_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "site.activate": "Site activated — {name}",
    "site.deactivate": "Site deactivated — {name}",
    "site.archive": "Site archived — {name}",
}
_SITE_STATUS_EVENT_CLASS: dict[str, type] = {
    "site.activate": SiteActivated,
    "site.deactivate": SiteDeactivated,
    "site.archive": SiteArchived,
}


def _require_valid_site_transition(site: Site, new_status: str) -> None:
    if site.status == new_status:
        raise ValidationError(
            f"Site is already {new_status}.",
            code=f"SITE_ALREADY_{new_status.upper()}",
        )
    if site.status == SITE_STATUS_ARCHIVED:
        raise ValidationError(
            "Archived sites cannot be reactivated or deactivated directly.",
            code="SITE_ARCHIVED",
        )
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.site_unit_of_work import (
    SiteUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class SiteCommandHandler:
    """Site lifecycle writes in the active organization: create, update, activate,
    deactivate and archive, each in one Site UoW with audit and activity."""

    def __init__(
        self,
        *,
        uow_factory: SiteUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_site(self, command: SiteCreateCommand) -> Site:
        """Lifecycle is never settable through Create -- every new site starts
        ACTIVE. Use activate_site/deactivate_site/archive_site afterward for any
        non-active initial state a test or import needs."""
        require_permission(self._user_session, "settings.manage", operation_label="create site")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        now = datetime.now(UTC)
        site = Site.create(
            organization_id=organization.id,
            site_code=command.site_code,
            name=command.name,
            description=command.description,
            country=command.country,
            region=command.region,
            city=command.city,
            address_line_1=command.address_line_1,
            address_line_2=command.address_line_2,
            postal_code=command.postal_code,
            timezone=normalize_optional_text(command.timezone_name) or organization.timezone_name,
            currency_code=normalize_optional_text(command.currency_code) or organization.base_currency,
            site_type=command.site_type,
            status=SITE_STATUS_ACTIVE,
            # Legacy field: references working_calendars.id. Not read by the enterprise
            # CalendarResolver -- which uses site_calendar_assignments instead and falls
            # back to the GLOBAL platform_calendar. Kept for backward-compat data export.
            default_calendar_id=normalize_optional_text(command.default_calendar_id) or "default",
            default_language=command.default_language,
            opened_at=command.opened_at or now,
            closed_at=command.closed_at,
            notes=command.notes,
        )
        with self._uow_factory.create(context=_new_context()) as uow:
            if uow.sites.get_by_code(organization.id, site.site_code) is not None:
                raise ValidationError(
                    "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
                )
            try:
                uow.sites.add(site)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="site",
                    entity_id=site.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"site_code": site.site_code, "name": site.name},
                    metadata={"action": "site.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="site.create",
                    entity_type="site",
                    entity_id=site.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Site created — {site.name}",
                    icon="site",
                    commit=False,
                )
                uow.record_event(
                    SiteCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        site_id=site.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
                ) from exc
        return site

    def update_site(self, command: SiteUpdateCommand) -> Site:
        """Pure profile update -- lifecycle (status/is_active) is never accepted
        here; it can only change through activate_site/deactivate_site/
        archive_site below, each with its own guarded transition, audit entry,
        and activity message. opened_at/closed_at stay directly editable here as
        a genuine, independent business timeline (e.g. correcting a historical
        date), no longer auto-stamped as a side effect of a status change."""
        require_permission(self._user_session, "settings.manage", operation_label="update site")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            site = uow.sites.get(command.site_id)
            if site is None or site.organization_id != organization.id:
                raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
            if command.expected_version is not None and site.version != command.expected_version:
                raise ConcurrencyError(
                    "Site changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )
            now = datetime.now(UTC)
            candidate = replace(
                site,
                site_code=site.site_code if command.site_code is None else command.site_code,
                # A missing name is rejected by the field's "before" validator.
                name=site.name if command.name is None else command.name,
                description=site.description if command.description is None else command.description,
                country=site.country if command.country is None else command.country,
                region=site.region if command.region is None else command.region,
                city=site.city if command.city is None else command.city,
                address_line_1=site.address_line_1 if command.address_line_1 is None else command.address_line_1,
                address_line_2=site.address_line_2 if command.address_line_2 is None else command.address_line_2,
                postal_code=site.postal_code if command.postal_code is None else command.postal_code,
                timezone=site.timezone if command.timezone_name is None else command.timezone_name,
                currency_code=site.currency_code if command.currency_code is None else command.currency_code,
                site_type=site.site_type if command.site_type is None else command.site_type,
                default_calendar_id=site.default_calendar_id if command.default_calendar_id is None else command.default_calendar_id,
                default_language=site.default_language if command.default_language is None else command.default_language,
                opened_at=site.opened_at if command.opened_at is None else command.opened_at,
                closed_at=site.closed_at if command.closed_at is None else command.closed_at,
                notes=site.notes if command.notes is None else command.notes,
            )
            profile_changed = (
                candidate.site_code != site.site_code
                or candidate.name != site.name
                or candidate.description != site.description
                or candidate.country != site.country
                or candidate.region != site.region
                or candidate.city != site.city
                or candidate.address_line_1 != site.address_line_1
                or candidate.address_line_2 != site.address_line_2
                or candidate.postal_code != site.postal_code
                or candidate.timezone != site.timezone
                or candidate.currency_code != site.currency_code
                or candidate.site_type != site.site_type
                or candidate.default_calendar_id != site.default_calendar_id
                or candidate.default_language != site.default_language
                or candidate.notes != site.notes
                or candidate.opened_at != site.opened_at
                or candidate.closed_at != site.closed_at
            )
            if not profile_changed:
                return site
            candidate = replace(candidate, updated_at=now)
            existing = uow.sites.get_by_code(organization.id, candidate.site_code)
            if existing is not None and existing.id != site.id:
                raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
            try:
                uow.sites.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="site",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    metadata={"action": "site.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="site.update",
                    entity_type="site",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Site updated — {candidate.name}",
                    icon="site",
                    commit=False,
                )
                uow.record_event(
                    SiteProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        site_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
                ) from exc
        return candidate

    def _transition_site_status(
        self, site_id: str, *, new_status: str, action: str
    ) -> Site:
        require_permission(self._user_session, "settings.manage", operation_label="change site status")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            site = uow.sites.get(site_id)
            if site is None or site.organization_id != organization.id:
                raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
            _require_valid_site_transition(site, new_status)
            now = datetime.now(UTC)
            next_opened_at = site.opened_at
            next_closed_at = site.closed_at
            if new_status == SITE_STATUS_ACTIVE and next_opened_at is None:
                next_opened_at = now
            if new_status == SITE_STATUS_ARCHIVED and next_closed_at is None:
                next_closed_at = now
            candidate = replace(
                site,
                status=new_status,
                opened_at=next_opened_at,
                closed_at=next_closed_at,
                updated_at=now,
            )
            uow.sites.update(candidate)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="site",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                category="PRIVILEGED_OPERATION",
                severity=_SITE_STATUS_AUDIT_SEVERITY[action],
                changed_fields={"status": {"before": site.status, "after": candidate.status}},
                after_data={"site_code": candidate.site_code, "name": candidate.name, "status": candidate.status},
                metadata={"action": action},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action=action,
                entity_type="site",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                message=_SITE_STATUS_ACTIVITY_MESSAGE[action].format(name=candidate.name),
                icon="site",
                type="info" if action == "site.activate" else "warning",
                commit=False,
            )
            uow.record_event(
                _SITE_STATUS_EVENT_CLASS[action](
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    site_id=candidate.id,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        return candidate

    def activate_site(self, site_id: str) -> Site:
        return self._transition_site_status(site_id, new_status=SITE_STATUS_ACTIVE, action="site.activate")

    def deactivate_site(self, site_id: str) -> Site:
        return self._transition_site_status(site_id, new_status=SITE_STATUS_INACTIVE, action="site.deactivate")

    def archive_site(self, site_id: str) -> Site:
        return self._transition_site_status(site_id, new_status=SITE_STATUS_ARCHIVED, action="site.archive")


__all__ = ["SiteCommandHandler"]
