from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.tenant.tenancy.models.tenant import TenantDto, TenantInvitationDto
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.application.tenant.tenancy.tenant_admin_service import TenantAdminService
from src.core.platform.application.tenant.tenancy.tenant_membership_service import TenantMembershipService
from src.core.platform.domain.tenant.tenancy import Tenant, UserTenantMembership
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService


class PlatformTenantDesktopApi:
    """Desktop-facing adapter for tenant switching and listing accessible tenants."""

    def __init__(
        self,
        *,
        tenant_admin_service: TenantAdminService,
        tenant_context_service: TenantContextService,
        tenant_membership_service: TenantMembershipService | None = None,
    ) -> None:
        self._tenant_admin_service = tenant_admin_service
        self._tenant_context_service = tenant_context_service
        self._tenant_membership_service = tenant_membership_service

    def list_accessible_tenants(self) -> DesktopApiResult[tuple[TenantDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_tenant(t)
                for t in self._tenant_admin_service.list_accessible_tenants()
            )
        )

    def get_active_tenant(self) -> DesktopApiResult[TenantDto | None]:
        return execute_desktop_operation(
            lambda: self._serialize_tenant(tenant)
            if (tenant := self._tenant_context_service.get_active_tenant()) is not None
            else None
        )

    def switch_to_tenant(self, tenant_id: str) -> DesktopApiResult[TenantDto]:
        return execute_desktop_operation(
            lambda: self._serialize_tenant(
                self._tenant_context_service.switch_to_tenant(tenant_id)
            )
        )

    def list_pending_invitations(
        self,
    ) -> DesktopApiResult[tuple[TenantInvitationDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_invitation(membership)
                for membership in self._require_membership_service().list_my_pending_invitations()
            )
        )

    def accept_invitation(
        self,
        tenant_id: str,
    ) -> DesktopApiResult[TenantInvitationDto]:
        return execute_desktop_operation(
            lambda: self._serialize_invitation(
                self._require_membership_service().accept_invitation_for_tenant(
                    tenant_id
                )
            )
        )

    @staticmethod
    def _serialize_tenant(tenant: Tenant) -> TenantDto:
        return TenantDto(
            id=tenant.id,
            tenant_code=tenant.tenant_code,
            display_name=tenant.display_name,
            tenant_status=tenant.tenant_status,
            is_active=tenant.is_active,
        )

    @staticmethod
    def _serialize_invitation(
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

    def _require_membership_service(self) -> TenantMembershipService:
        if self._tenant_membership_service is None:
            raise BusinessRuleError(
                "Tenant invitation service is not configured.",
                code="TENANT_INVITATION_SERVICE_REQUIRED",
            )
        return self._tenant_membership_service


__all__ = ["PlatformTenantDesktopApi"]
