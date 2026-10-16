from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

import src.core.platform.application.master_data.org.mappers.organization as response_mapper
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.application.master_data.org.organization_context import (
    require_current_tenant_id,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.organization_unit_of_work import (
    OrganizationUnitOfWorkFactory,
)
from src.core.platform.domain.master_data.org import (
    ORGANIZATION_STATUS_ACTIVE,
    ORGANIZATION_STATUS_ARCHIVED,
    ORGANIZATION_STATUS_INACTIVE,
    Organization,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationDeactivated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
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


class OrganizationLifecycleCommandHandler:
    """Organization lifecycle transitions (activate, deactivate, archive), singly
    and in bulk, each in one Organization UoW; clears a no-longer-active session selection."""

    def __init__(
        self,
        *,
        uow_factory: OrganizationUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session

    def activate_organization(self, organization_id: str) -> OrganizationDto:
        return response_mapper.serialize_organization(self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_ACTIVE, action="organization.activate"
        ))

    def deactivate_organization(self, organization_id: str) -> OrganizationDto:
        return response_mapper.serialize_organization(self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_INACTIVE, action="organization.deactivate"
        ))

    def archive_organization(self, organization_id: str) -> OrganizationDto:
        return response_mapper.serialize_organization(self._transition_organization_status(
            organization_id, new_status=ORGANIZATION_STATUS_ARCHIVED, action="organization.archive"
        ))

    def bulk_activate_organizations(self, organization_ids: Sequence[str]) -> list[OrganizationDto]:
        return [response_mapper.serialize_organization(row) for row in (self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_ACTIVE, action="organization.activate"
        ))]

    def bulk_deactivate_organizations(self, organization_ids: Sequence[str]) -> list[OrganizationDto]:
        return [response_mapper.serialize_organization(row) for row in (self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_INACTIVE, action="organization.deactivate"
        ))]

    def bulk_archive_organizations(self, organization_ids: Sequence[str]) -> list[OrganizationDto]:
        return [response_mapper.serialize_organization(row) for row in (self._bulk_transition_organization_status(
            organization_ids, new_status=ORGANIZATION_STATUS_ARCHIVED, action="organization.archive"
        ))]

    def _transition_organization_status(
        self, organization_id: str, *, new_status: str, action: str
    ) -> Organization:
        require_permission(
            self._user_session, "settings.manage", operation_label="change organization status"
        )
        tenant_id = require_current_tenant_id(self._user_session, operation_label="change organization status")
        with self._uow_factory.create(context=_new_context()) as uow:
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
        tenant_id = require_current_tenant_id(self._user_session, operation_label="change organization status")
        results: list[Organization] = []
        with self._uow_factory.create(context=_new_context()) as uow:
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


__all__ = ["OrganizationLifecycleCommandHandler"]
