from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.party.party_context import (
    active_organization,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.party_unit_of_work import (
    PartyUnitOfWorkFactory,
)
from src.core.platform.contract.use_cases.master_data.party.commands import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.domain.master_data.party import (
    Party,
    PartyLifecycleStatus,
    PartyRole,
    PartyType,
)
from src.core.platform.domain.master_data.party.events import (
    PartyActivated,
    PartyCreated,
    PartyDeactivated,
    PartyProfileUpdated,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

PARTY_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)



if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext

_PARTY_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "party.activate": "Party reinstated - {name}",
    "party.deactivate": "Party removed - {name}",
}
_PARTY_STATUS_EVENT_CLASS: dict[str, type] = {
    "party.activate": PartyActivated,
    "party.deactivate": PartyDeactivated,
}


class PartyCommandHandler:
    """Party lifecycle writes in the active organization: create, update, activate
    and deactivate, each in one Party UoW with audit and activity."""

    def __init__(
        self,
        *,
        uow_factory: PartyUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_party(self, command: PartyCreateCommand) -> Party:
        # No `is_active`/`status` parameter -- every new Party starts
        # ACTIVE (PartyLifecycleStatus's own default). Use
        # activate_party/deactivate_party afterward to change it.
        require_permission(self._user_session, "party.manage", operation_label="create party")
        organization = active_organization(self._tenant_context_service)
        # Active-context organizations are tenant-scoped.
        tenant_id = cast(str, organization.tenant_id)
        party = Party.create(
            organization_id=organization.id,
            party_code=command.party_code,
            # A missing name is rejected by Party's "before" validator.
            party_name=cast(str, command.party_name),
            party_type=command.party_type,
            roles=command.roles,
            legal_name=command.legal_name,
            contact_name=command.contact_name,
            email=command.email or "",
            phone=command.phone or "",
            country=command.country,
            city=command.city,
            address_line_1=command.address_line_1,
            address_line_2=command.address_line_2,
            postal_code=command.postal_code,
            website=command.website,
            registration_number=command.registration_number,
            tax_identifier=command.tax_identifier,
            external_reference=command.external_reference,
            notes=command.notes,
        )
        with self._uow_factory.create(context=_new_context()) as uow:
            if uow.parties.get_by_code(organization.id, party.party_code) is not None:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                )
            try:
                uow.parties.add(party)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="party",
                    entity_id=party.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"party_code": party.party_code, "party_name": party.party_name},
                    metadata={"action": "party.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="party.create",
                    entity_type="party",
                    entity_id=party.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Party created — {party.party_name}",
                    icon="party",
                    commit=False,
                )
                uow.record_event(
                    PartyCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        party_id=party.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                ) from exc
        return party

    def update_party(self, command: PartyUpdateCommand) -> Party:
        # No `is_active`/`status` parameter here either -- lifecycle changes
        # only ever happen through activate_party/deactivate_party.
        require_permission(self._user_session, "party.manage", operation_label="update party")
        organization = active_organization(self._tenant_context_service)
        # Active-context organizations are tenant-scoped.
        tenant_id = cast(str, organization.tenant_id)
        with self._uow_factory.create(context=_new_context()) as uow:
            party = uow.parties.get(command.party_id)
            if party is None or party.organization_id != organization.id:
                raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
            if command.expected_version is not None and party.version != command.expected_version:
                raise ConcurrencyError(
                    "Party changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            candidate = replace(
                party,
                party_code=command.party_code if command.party_code is not None else party.party_code,
                party_name=command.party_name if command.party_name is not None else party.party_name,
                # Raw inputs are coerced by the fields' "before" validators.
                party_type=cast(
                    PartyType, command.party_type if command.party_type is not None else party.party_type
                ),
                roles=cast("tuple[PartyRole, ...]", command.roles if command.roles is not None else party.roles),
                legal_name=command.legal_name if command.legal_name is not None else party.legal_name,
                contact_name=command.contact_name if command.contact_name is not None else party.contact_name,
                email=command.email if command.email is not None else party.email,
                phone=command.phone if command.phone is not None else party.phone,
                country=command.country if command.country is not None else party.country,
                city=command.city if command.city is not None else party.city,
                address_line_1=command.address_line_1 if command.address_line_1 is not None else party.address_line_1,
                address_line_2=command.address_line_2 if command.address_line_2 is not None else party.address_line_2,
                postal_code=command.postal_code if command.postal_code is not None else party.postal_code,
                website=command.website if command.website is not None else party.website,
                registration_number=(
                    command.registration_number if command.registration_number is not None else party.registration_number
                ),
                tax_identifier=command.tax_identifier if command.tax_identifier is not None else party.tax_identifier,
                external_reference=command.external_reference if command.external_reference is not None else party.external_reference,
                notes=command.notes if command.notes is not None else party.notes,
            )
            profile_changed = (
                candidate.party_code != party.party_code
                or candidate.party_name != party.party_name
                or candidate.party_type != party.party_type
                or candidate.roles != party.roles
                or candidate.legal_name != party.legal_name
                or candidate.contact_name != party.contact_name
                or candidate.email != party.email
                or candidate.phone != party.phone
                or candidate.country != party.country
                or candidate.city != party.city
                or candidate.address_line_1 != party.address_line_1
                or candidate.address_line_2 != party.address_line_2
                or candidate.postal_code != party.postal_code
                or candidate.website != party.website
                or candidate.registration_number != party.registration_number
                or candidate.tax_identifier != party.tax_identifier
                or candidate.external_reference != party.external_reference
                or candidate.notes != party.notes
            )
            if not profile_changed:
                return party
            candidate = replace(candidate, updated_at=datetime.now(UTC))
            if command.party_code is not None:
                existing = uow.parties.get_by_code(organization.id, candidate.party_code)
                if existing is not None and existing.id != party.id:
                    raise ValidationError(
                        "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                    )

            try:
                uow.parties.update(candidate)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="party",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    metadata={"action": "party.update"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="party.update",
                    entity_type="party",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Party updated — {candidate.party_name}",
                    icon="party",
                    commit=False,
                )
                uow.record_event(
                    PartyProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        party_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Party code already exists in the active organization.", code="PARTY_CODE_EXISTS"
                ) from exc
        return candidate


    def _transition_party_status(
        self, party_id: str, *, new_status: PartyLifecycleStatus, action: str
    ) -> Party:
        require_permission(self._user_session, "party.manage", operation_label="change party status")
        organization = active_organization(self._tenant_context_service)
        tenant_id = organization.tenant_id
        with self._uow_factory.create(context=_new_context()) as uow:
            party = uow.parties.get(party_id)
            if party is None or party.organization_id != organization.id:
                raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
            _require_valid_party_transition(party, new_status)
            candidate = replace(party, status=new_status, updated_at=datetime.now(UTC))
            uow.parties.update(candidate)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="party",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                category="MASTER_DATA",
                severity="low",
                changed_fields={"status": {"before": party.status.value, "after": candidate.status.value}},
                metadata={"action": action},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action=action,
                entity_type="party",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                message=_PARTY_STATUS_ACTIVITY_MESSAGE[action].format(name=candidate.party_name),
                icon="party",
                type="warning" if action == "party.deactivate" else "info",
                commit=False,
            )
            uow.record_event(
                _PARTY_STATUS_EVENT_CLASS[action](
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    party_id=candidate.id,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        return candidate

    def activate_party(self, party_id: str) -> Party:
        return self._transition_party_status(
            party_id, new_status=PartyLifecycleStatus.ACTIVE, action="party.activate"
        )

    def deactivate_party(self, party_id: str) -> Party:
        """Deactivation makes a Party unselectable for NEW operational links
        (a new Project client, a new Commitment supplier) -- it never cascades
        to existing PM references, Documents, or Activity history, all of
        which remain fully readable. Enforcing "not selectable for new links"
        is PM's own responsibility at the point of creating those new links,
        not something Party itself needs to guard here."""
        return self._transition_party_status(
            party_id, new_status=PartyLifecycleStatus.INACTIVE, action="party.deactivate"
        )


def _require_valid_party_transition(party: Party, new_status: PartyLifecycleStatus) -> None:
    if party.status == new_status:
        raise ValidationError(
            f"Party is already {new_status.value}.",
            code=f"PARTY_ALREADY_{new_status.value.upper()}",
        )


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["PartyCommandHandler"]
