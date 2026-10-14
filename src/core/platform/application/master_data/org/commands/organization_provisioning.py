from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext

if TYPE_CHECKING:
    from src.core.platform.application.master_data.org.commands.organization_commands import (
        OrganizationCommandHandler,
    )
    from src.core.platform.application.master_data.org.dto import (
        OrganizationProvisionCommand,
    )
    from src.core.platform.application.master_data.org.queries import (
        OrganizationQueryHandler,
    )
    from src.core.platform.application.tenant.modules import (
        ModuleCatalogQueryHandler,
        ModuleEntitlementProvisioningHandler,
    )
    from src.core.platform.application.tenant.tenancy import TenantContextService
    from src.core.platform.contract.uow.provisioning.platform_provisioning_unit_of_work import (
        PlatformProvisioningUnitOfWorkFactory,
    )
    from src.core.platform.domain.master_data.org import Organization
    from src.core.platform.domain.security.auth.session import UserSessionContext


class OrganizationProvisioningCommandHandler:
    """Provision an organization and its entitlements in one fresh-session UoW."""

    def __init__(
        self,
        *,
        module_catalog_service: ModuleCatalogQueryHandler,
        module_entitlement_provisioning: ModuleEntitlementProvisioningHandler,
        organization_query: OrganizationQueryHandler,
        organization_commands: OrganizationCommandHandler,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext,
        provisioning_uow_factory: PlatformProvisioningUnitOfWorkFactory,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._module_entitlement_provisioning = module_entitlement_provisioning
        self._organization_query = organization_query
        self._organization_commands = organization_commands
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._provisioning_uow_factory = provisioning_uow_factory

    def provision_organization(self, command: OrganizationProvisionCommand) -> Organization:
        if self._organization_commands is None or self._organization_query is None:
            raise RuntimeError("Organization service is not configured.")
        if self._provisioning_uow_factory is None:
            raise RuntimeError("Provisioning UnitOfWork factory is not configured.")
        if self._module_entitlement_provisioning is None:
            raise RuntimeError("Module entitlement provisioning is not configured.")
        module_entitlement_provisioning = self._module_entitlement_provisioning

        require_permission(self._user_session, "settings.manage", operation_label="provision organization")
        tenant_id = self._organization_query.require_current_tenant_id(
            operation_label="provision organization"
        )
        require_permission(
            self._user_session, "settings.manage",
            operation_label="set active organization context",
        )

        selected_module_codes = (
            set(command.initial_module_codes)
            if command.initial_module_codes is not None
            else {
                module.code
                for module in self._module_catalog_service.list_modules()
                if module.default_enabled and module.stage != "planned"
            }
        )

        context = DomainEventContext(correlation_id=generate_id())
        with self._provisioning_uow_factory.create(context=context) as uow:
            try:
                organization = self._organization_commands.create_organization_using(
                    uow.organizations,
                    uow,
                    organization_code=command.organization_code,
                    display_name=command.display_name,
                    timezone_name=command.timezone_name,
                    base_currency=command.base_currency,
                    tenant_id=tenant_id,
                    legal_name=command.legal_name,
                    registration_number=command.registration_number,
                    tax_id=command.tax_id,
                    address_line_1=command.address_line_1,
                    address_line_2=command.address_line_2,
                    postal_code=command.postal_code,
                    city=command.city,
                    state_region=command.state_region,
                    country_code=command.country_code,
                    email=command.email,
                    phone=command.phone,
                    website=command.website,
                )
                module_entitlement_provisioning.provision_organization_entitlements_using(
                    uow,
                    organization.id,
                    licensed_module_codes=selected_module_codes,
                    enabled_module_codes=selected_module_codes,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        if self._tenant_context_service is None:
            raise RuntimeError("Tenant context service is not configured.")
        self._tenant_context_service.set_active_organization(organization.id)
        module_entitlement_provisioning.notify_module_entitlements_stale(organization.id)
        return organization
