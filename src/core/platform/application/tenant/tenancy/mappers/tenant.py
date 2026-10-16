from __future__ import annotations

from src.core.platform.application.tenant.tenancy.dto.responses.tenant import (
    TenantDto,
    TenantInvitationDto,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.tenant.tenancy import Tenant, UserTenantMembership


def serialize_tenant(tenant: Tenant) -> TenantDto:
    return TenantDto(
        id=tenant.id,
        tenant_code=tenant.tenant_code,
        display_name=tenant.display_name,
        tenant_status=tenant.tenant_status,
        is_active=tenant.is_active,
    )


def serialize_invitation(
    membership: UserTenantMembership,
) -> TenantInvitationDto:
    if membership.invited_at is None or membership.invitation_expires_at is None:
        raise BusinessRuleError(
            "Tenant invitation metadata is incomplete.",
            code="TENANT_INVITATION_METADATA_INVALID",
        )
    return TenantInvitationDto(
        membership_id=membership.id,
        tenant_id=membership.tenant_id,
        status=membership.status,
        invited_by_user_id=membership.invited_by_user_id,
        invited_at=membership.invited_at,
        expires_at=membership.invitation_expires_at,
    )
