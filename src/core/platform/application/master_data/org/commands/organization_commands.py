from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.org.organization_context import (
    require_current_tenant_id,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.org.default_calendar_writer import (
    OrganizationDefaultCalendarWriter,
)
from src.core.platform.contract.uow.master_data.organization_unit_of_work import (
    OrganizationUnitOfWorkFactory,
)
from src.core.platform.contract.use_cases.master_data.org.commands import (
    OrganizationUpdateCommand,
)
from src.core.platform.domain.master_data.org import (
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
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import UnitOfWork
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext

logger = logging.getLogger(__name__)

ORGANIZATION_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)

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

def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class OrganizationCommandHandler:
    """Organization profile writes: bootstrap of the default organization, create
    (with its default calendar in the same UoW), update, and bulk currency/timezone."""

    def __init__(
        self,
        *,
        organization_repo: OrganizationRepository,
        uow_factory: OrganizationUnitOfWorkFactory,
        default_calendar_writer: OrganizationDefaultCalendarWriter,
        clock: Clock,
        user_session: UserSessionContext | None,
    ) -> None:
        self._organization_repo = organization_repo
        self._uow_factory = uow_factory
        self._default_calendar_writer = default_calendar_writer
        self._clock = clock
        self._user_session = user_session

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
        with self._uow_factory.create(context=_new_context()) as uow:
            uow.organizations.add(organization)
            uow.commit()

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
        tenant_id = require_current_tenant_id(self._user_session, operation_label="create organization")
        with self._uow_factory.create(context=_new_context()) as uow:
            organization = self.create_organization_using(
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
            self._default_calendar_writer.add_default_calendar(uow.session, organization)
            try:
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        return organization

    def update_organization(self, command: OrganizationUpdateCommand) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = require_current_tenant_id(self._user_session, operation_label="update organization")
        with self._uow_factory.create(context=_new_context()) as uow:
            organization = uow.organizations.get_for_tenant(command.organization_id, tenant_id)
            if organization is None:
                raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
            if command.expected_version is not None and organization.version != command.expected_version:
                raise ConcurrencyError(
                    "Organization changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            candidate = replace(
                organization,
                organization_code=(
                    organization.organization_code
                    if command.organization_code is None
                    else command.organization_code
                ),
                display_name=organization.display_name if command.display_name is None else command.display_name,
                timezone_name=organization.timezone_name if command.timezone_name is None else command.timezone_name,
                base_currency=organization.base_currency if command.base_currency is None else command.base_currency,
                legal_name=organization.legal_name if command.legal_name is None else command.legal_name,
                registration_number=(
                    organization.registration_number if command.registration_number is None else command.registration_number
                ),
                tax_id=organization.tax_id if command.tax_id is None else command.tax_id,
                address_line_1=organization.address_line_1 if command.address_line_1 is None else command.address_line_1,
                address_line_2=organization.address_line_2 if command.address_line_2 is None else command.address_line_2,
                postal_code=organization.postal_code if command.postal_code is None else command.postal_code,
                city=organization.city if command.city is None else command.city,
                state_region=organization.state_region if command.state_region is None else command.state_region,
                country_code=organization.country_code if command.country_code is None else command.country_code,
                email=organization.email if command.email is None else command.email,
                phone=organization.phone if command.phone is None else command.phone,
                website=organization.website if command.website is None else command.website,
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
        tenant_id = require_current_tenant_id(self._user_session, operation_label="update organization")
        results: list[Organization] = []
        with self._uow_factory.create(context=_new_context()) as uow:
            for organization_id in organization_ids:
                organization = uow.organizations.get_for_tenant(organization_id, tenant_id)
                if organization is None:
                    raise NotFoundError(
                        f"Organization not found: {organization_id}", code="ORGANIZATION_NOT_FOUND"
                    )
                if getattr(organization, field_name) == value:
                    results.append(organization)
                    continue
                if field_name == "base_currency":
                    candidate = replace(organization, tenant_id=tenant_id, base_currency=value)
                elif field_name == "timezone_name":
                    candidate = replace(organization, tenant_id=tenant_id, timezone_name=value)
                else:
                    raise ValueError(f"Unsupported organization bulk field: {field_name}")
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

    def create_organization_using(
        self,
        organization_repo: OrganizationRepository,
        uow: UnitOfWork,
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


__all__ = ["OrganizationCommandHandler"]
