from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.master_data.party import Party, PartyLifecycleStatus
from src.core.platform.domain.master_data.party.events import (
    PartyActivated,
    PartyDeactivated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

if TYPE_CHECKING:
    from src.core.platform.application.master_data.party.party_service import (
        PartyService,
    )

_PARTY_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "party.activate": "Party reinstated - {name}",
    "party.deactivate": "Party removed - {name}",
}
_PARTY_STATUS_EVENT_CLASS: dict[str, type] = {
    "party.activate": PartyActivated,
    "party.deactivate": PartyDeactivated,
}


def _require_valid_party_transition(party: Party, new_status: PartyLifecycleStatus) -> None:
    if party.status == new_status:
        raise ValidationError(
            f"Party is already {new_status.value}.",
            code=f"PARTY_ALREADY_{new_status.value.upper()}",
        )


def _transition_party_status(
    service: PartyService, party_id: str, *, new_status: PartyLifecycleStatus, action: str
) -> Party:
    require_permission(service._user_session, "party.manage", operation_label="change party status")
    organization = service._active_organization()
    tenant_id = organization.tenant_id
    with service._uow_factory.create(context=service._new_context()) as uow:
        party = uow.parties.get(party_id)
        if party is None or party.organization_id != organization.id:
            raise NotFoundError("Party not found in the active organization.", code="PARTY_NOT_FOUND")
        _require_valid_party_transition(party, new_status)
        candidate = replace(party, status=new_status, updated_at=datetime.now(timezone.utc))
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
                occurred_at=service._clock.now(),
            )
        )
        uow.commit()
    return candidate


def activate_party(service: PartyService, party_id: str) -> Party:
    return _transition_party_status(
        service, party_id, new_status=PartyLifecycleStatus.ACTIVE, action="party.activate"
    )


def deactivate_party(service: PartyService, party_id: str) -> Party:
    """Deactivation makes a Party unselectable for NEW operational links
    (a new Project client, a new Commitment supplier) -- it never cascades
    to existing PM references, Documents, or Activity history, all of
    which remain fully readable. Enforcing "not selectable for new links"
    is PM's own responsibility at the point of creating those new links,
    not something Party itself needs to guard here."""
    return _transition_party_status(
        service, party_id, new_status=PartyLifecycleStatus.INACTIVE, action="party.deactivate"
    )


__all__ = ["activate_party", "deactivate_party"]
