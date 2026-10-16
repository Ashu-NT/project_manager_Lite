from __future__ import annotations

import src.core.platform.application.tenant.tenancy.mappers.tenant as response_mapper
from src.core.platform.application.tenant.tenancy.dto.responses.tenant import (
    TenantInvitationDto,
)
from src.core.platform.application.tenant.tenancy.membership_support import (
    TenantMembershipSupport,
)
from src.core.platform.contract.uow.tenancy.tenant_membership_unit_of_work import (
    TenantMembershipUnitOfWorkFactory,
)
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_INVITED,
)


class TenantMembershipQueryHandler:
    """Read only the authenticated recipient's unexpired pending invitations."""

    def __init__(
        self,
        *,
        uow_factory: TenantMembershipUnitOfWorkFactory,
        support: TenantMembershipSupport,
    ) -> None:
        self._uow_factory = uow_factory
        self._support = support

    def list_my_pending_invitations(self) -> list[TenantInvitationDto]:
        actor = self._support.require_authenticated_principal()
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            pending = [
                membership
                for membership in uow.memberships.list_memberships_for_user(
                    actor.user_id
                )
                if membership.status == MEMBERSHIP_STATUS_INVITED
                and not membership.invitation_is_expired()
            ]
            uow.commit()
        return [response_mapper.serialize_invitation(row) for row in (pending)]
