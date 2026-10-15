from __future__ import annotations

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.api.desktop.tenant.tenancy.models.tenant import (
    TenantDto,
    TenantInvitationDto,
)
from src.core.platform.application.tenant.tenancy.commands.invitations import (
    TenantInvitationCommandHandler,
)
from src.core.platform.application.tenant.tenancy.commands.tenant_lifecycle import (
    TenantLifecycleCommandHandler,
)
from src.core.platform.application.tenant.tenancy.dto.commands.tenants import (
    TenantCreateCommand,
)
from src.core.platform.application.tenant.tenancy.queries.admin import (
    TenantAdminQueryHandler,
)
from src.core.platform.application.tenant.tenancy.queries.membership import (
    TenantMembershipQueryHandler,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.tenant.tenancy import Tenant, UserTenantMembership


class PlatformTenantDesktopApi:
    """Desktop-facing adapter for tenant/organization switching and session working-context.

    Organization availability (enable/disable) lives on `PlatformRuntimeDesktopApi`;
    organization-scoped access grants live on `PlatformAccessDesktopApi`."""

    def __init__(
        self,
        *,
        tenant_admin_queries: TenantAdminQueryHandler,
        tenant_lifecycle_commands: TenantLifecycleCommandHandler,
        tenant_context_service: TenantContextService,
        tenant_invitation_commands: TenantInvitationCommandHandler,
        tenant_membership_queries: TenantMembershipQueryHandler,
    ) -> None:
        self._tenant_admin_queries = tenant_admin_queries
        self._tenant_lifecycle_commands = tenant_lifecycle_commands
        self._tenant_context_service = tenant_context_service
        self._tenant_invitation_commands = tenant_invitation_commands
        self._tenant_membership_queries = tenant_membership_queries

    def list_accessible_tenants(self) -> DesktopApiResult[tuple[TenantDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_tenant(t)
                for t in self._tenant_admin_queries.list_accessible_tenants()
            )
        )

    def list_accessible_organizations(
        self,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                serialize_organization(o)
                for o in self._tenant_context_service.list_accessible_organizations()
            )
        )

    def get_active_organization(self) -> DesktopApiResult[OrganizationDto | None]:
        return execute_desktop_operation(
            lambda: (
                serialize_organization(organization)
                if (
                    organization
                    := self._tenant_context_service.get_active_organization()
                )
                is not None
                else None
            )
        )

    def switch_to_organization(
        self, organization_id: str
    ) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(
                self._tenant_context_service.set_active_organization(organization_id)
            )
        )

    def create_tenant(
        self, command: TenantCreateCommand
    ) -> DesktopApiResult[TenantDto]:
        return execute_desktop_operation(
            lambda: self._serialize_tenant(
                self._tenant_lifecycle_commands.create_tenant(command)
            )
        )

    def get_active_tenant(self) -> DesktopApiResult[TenantDto | None]:
        return execute_desktop_operation(
            lambda: (
                self._serialize_tenant(tenant)
                if (tenant := self._tenant_context_service.get_active_tenant())
                is not None
                else None
            )
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
                for membership in self._tenant_membership_queries.list_my_pending_invitations()
            )
        )

    def accept_invitation(
        self,
        tenant_id: str,
    ) -> DesktopApiResult[TenantInvitationDto]:
        return execute_desktop_operation(
            lambda: self._serialize_invitation(
                self._tenant_invitation_commands.accept_invitation_for_tenant(tenant_id)
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


__all__ = ["PlatformTenantDesktopApi"]
