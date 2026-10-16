from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
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
from src.core.platform.application.tenant.tenancy.dto.responses.tenant import (
    TenantDto,
    TenantInvitationDto,
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
                t
                for t in self._tenant_admin_queries.list_accessible_tenants()
            )
        )

    def list_accessible_organizations(
        self,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                o
                for o in self._tenant_context_service.list_accessible_organizations()
            )
        )

    def get_active_organization(self) -> DesktopApiResult[OrganizationDto | None]:
        return execute_desktop_operation(
            lambda: (
                organization
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
            lambda: self._tenant_context_service.set_active_organization(organization_id)
        )

    def create_tenant(
        self, command: TenantCreateCommand
    ) -> DesktopApiResult[TenantDto]:
        return execute_desktop_operation(
            lambda: self._tenant_lifecycle_commands.create_tenant(command)
        )

    def get_active_tenant(self) -> DesktopApiResult[TenantDto | None]:
        return execute_desktop_operation(
            lambda: (
                tenant
                if (tenant := self._tenant_context_service.get_active_tenant())
                is not None
                else None
            )
        )

    def switch_to_tenant(self, tenant_id: str) -> DesktopApiResult[TenantDto]:
        return execute_desktop_operation(
            lambda: self._tenant_context_service.switch_to_tenant(tenant_id)
        )

    def list_pending_invitations(
        self,
    ) -> DesktopApiResult[tuple[TenantInvitationDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                membership
                for membership in self._tenant_membership_queries.list_my_pending_invitations()
            )
        )

    def accept_invitation(
        self,
        tenant_id: str,
    ) -> DesktopApiResult[TenantInvitationDto]:
        return execute_desktop_operation(
            lambda: self._tenant_invitation_commands.accept_invitation_for_tenant(tenant_id)
        )




__all__ = ["PlatformTenantDesktopApi"]
