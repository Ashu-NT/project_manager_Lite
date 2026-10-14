from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationPage,
    OrganizationQueryHandler,
)
from src.core.platform.application.platform_runtime.module_access_policy import (
    is_module_accessible,
)
from src.core.platform.application.platform_runtime.module_snapshot import (
    build_module_runtime_snapshot,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementProvisioningHandler,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.provisioning.platform_provisioning_unit_of_work import (
    PlatformProvisioningUnitOfWorkFactory,
)
from src.core.platform.contract.use_cases.master_data.org.commands import (
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.contract.use_cases.platform_runtime import ModuleRuntimeSnapshot
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext


@dataclass(frozen=True)
class PlatformRuntimeContextSnapshot:
    context_label: str
    module_snapshot: ModuleRuntimeSnapshot


class PlatformRuntimeApplicationService:
    """Application-facing seam for active platform runtime context.

    Desktop UI and transport adapters use this orchestration contract instead
    of depending on shell-specific code or lower-level runtime services.
    """

    def __init__(
        self,
        *,
        module_catalog_service: ModuleCatalogQueryHandler,
        module_entitlement_provisioning: ModuleEntitlementProvisioningHandler | None = None,
        organization_query: OrganizationQueryHandler | None = None,
        organization_commands: OrganizationCommandHandler | None = None,
        organization_lifecycle: OrganizationLifecycleCommandHandler | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session: UserSessionContext | None = None,
        provisioning_uow_factory: PlatformProvisioningUnitOfWorkFactory | None = None,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._module_entitlement_provisioning = module_entitlement_provisioning
        self._organization_query = organization_query
        self._organization_commands = organization_commands
        self._organization_lifecycle = organization_lifecycle
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._provisioning_uow_factory = provisioning_uow_factory

    @property
    def module_catalog_service(self) -> ModuleCatalogQueryHandler:
        return self._module_catalog_service

    @property
    def organization_query(self) -> OrganizationQueryHandler | None:
        return self._organization_query

    @property
    def tenant_context_service(self) -> TenantContextService | None:
        return self._tenant_context_service

    @property
    def user_session(self) -> UserSessionContext | None:
        return self._user_session

    def get_current_permissions(self) -> frozenset[str]:
        """The current session principal's effective permission codes.

        Used by the QML shell to hide navigation destinations/actions the
        current user has no backend permission for, rather than showing
        them and letting the resulting desktop-API call fail server-side.
        Returns an empty set (nothing visible) if there is no authenticated
        principal, matching the fail-closed posture used everywhere else.
        """
        if self._user_session is None or self._user_session.principal is None:
            return frozenset()
        return frozenset(self._user_session.principal.permissions)

    def list_modules(self):
        return self._module_catalog_service.list_modules()

    def list_platform_capabilities(self):
        return self._module_catalog_service.list_platform_capabilities()

    def list_entitlements(self):
        return self._module_catalog_service.list_entitlements()

    def list_licensed_modules(self):
        return self._module_catalog_service.list_licensed_modules()

    def list_enabled_modules(self):
        return self._module_catalog_service.list_enabled_modules()

    def list_accessible_modules(self):
        """Enabled modules the current user also has permission to use.

        The single authoritative enabled+accessible definition -- see
        `module_access_policy.py`. An enabled module is not necessarily
        accessible: a module can be turned on for the organization while
        the current user holds no permission relevant to it.
        """
        permissions = self.get_current_permissions()
        return tuple(
            module
            for module in self.list_enabled_modules()
            if is_module_accessible(module.code, permissions)
        )

    def list_available_modules(self):
        return self._module_catalog_service.list_available_modules()

    def list_planned_modules(self):
        return self._module_catalog_service.list_planned_modules()

    def enabled_capability_codes(self) -> tuple[str, ...]:
        return self._module_catalog_service.enabled_capability_codes()

    def is_licensed(self, module_code: str) -> bool:
        return self._module_catalog_service.is_licensed(module_code)

    def is_enabled(self, module_code: str) -> bool:
        return self._module_catalog_service.is_enabled(module_code)

    def get_entitlement(self, module_code: str):
        return self._module_catalog_service.get_entitlement(module_code)

    def shell_summary(self) -> str:
        return self._module_catalog_service.shell_summary()

    def current_context_label(self) -> str:
        return self._module_catalog_service.current_context_label()

    def snapshot(self) -> PlatformRuntimeContextSnapshot:
        module_snapshot = build_module_runtime_snapshot(self._module_catalog_service)
        return PlatformRuntimeContextSnapshot(
            context_label=module_snapshot.context_label,
            module_snapshot=module_snapshot,
        )

    def list_organizations(self, *, status: str | None = None) -> list[Organization]:
        if self._organization_query is None:
            return []
        return self._organization_query.list_organizations(status=status)

    def list_organizations_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        status: str | None = None,
    ) -> OrganizationPage:
        if self._organization_query is None:
            return OrganizationPage(page=page, page_size=page_size)
        return self._organization_query.list_organizations_page(
            page=page, page_size=page_size, search=search, status=status
        )

    def get_organization_statistics(self, organization_id: str):
        from src.core.platform.application.master_data.org import (
            OrganizationStatistics,
        )

        if self._organization_query is None:
            return OrganizationStatistics()
        return self._organization_query.get_organization_statistics(organization_id)

    def get_organization_calendar_summary(self, organization_id: str):
        from src.core.platform.application.master_data.org import (
            OrganizationCalendarSummary,
        )

        if self._organization_query is None:
            return OrganizationCalendarSummary()
        return self._organization_query.get_organization_calendar_summary(organization_id)

    def get_organization_recent_activity(self, organization_id: str, *, limit: int = 5):
        if self._organization_query is None:
            return []
        return self._organization_query.get_organization_recent_activity(organization_id, limit=limit)

    def get_organization_count(self) -> int:
        if self._organization_query is None:
            return 0
        return self._organization_query.get_organization_count()

    def get_active_organization(self) -> Organization | None:
        if self._tenant_context_service is not None:
            return self._tenant_context_service.get_active_organization()
        return None

    def create_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str,
        base_currency: str,
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
        if self._organization_commands is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_commands.create_organization(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
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

    def update_organization(self, command: OrganizationUpdateCommand) -> Organization:
        if self._organization_commands is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_commands.update_organization(command)

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
        self._require_settings_manage("set active organization context")

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

    def activate_organization(self, organization_id: str) -> Organization:
        # Lifecycle mutation only -- never touches session/tenant context. Selecting this
        # organization as the acting user's working context is a separate action
        # (`TenantContextService.set_active_organization`).
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.activate_organization(organization_id)

    def deactivate_organization(self, organization_id: str) -> Organization:
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.deactivate_organization(organization_id)

    def archive_organization(self, organization_id: str) -> Organization:
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.archive_organization(organization_id)

    def bulk_activate_organizations(
        self, organization_ids: list[str] | tuple[str, ...]
    ) -> list[Organization]:
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.bulk_activate_organizations(organization_ids)

    def bulk_deactivate_organizations(
        self, organization_ids: list[str] | tuple[str, ...]
    ) -> list[Organization]:
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.bulk_deactivate_organizations(organization_ids)

    def bulk_archive_organizations(
        self, organization_ids: list[str] | tuple[str, ...]
    ) -> list[Organization]:
        if self._organization_lifecycle is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_lifecycle.bulk_archive_organizations(organization_ids)

    def bulk_update_organization_currency(
        self, organization_ids: list[str] | tuple[str, ...], base_currency: str
    ) -> list[Organization]:
        if self._organization_commands is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_commands.bulk_update_organization_currency(organization_ids, base_currency)

    def bulk_update_organization_timezone(
        self, organization_ids: list[str] | tuple[str, ...], timezone_name: str
    ) -> list[Organization]:
        if self._organization_commands is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_commands.bulk_update_organization_timezone(organization_ids, timezone_name)

    def _require_settings_manage(self, operation_label: str) -> None:
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label=operation_label,
        )


def resolve_platform_runtime_application_service(
    *,
    platform_runtime_application_service: object | None,
    module_catalog_service: object | None,
    organization_query: OrganizationQueryHandler | None = None,
    tenant_context_service: TenantContextService | None = None,
    user_session: UserSessionContext | None = None,
) -> object | None:
    if isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService) and (
        module_catalog_service is None
        or (
            platform_runtime_application_service.module_catalog_service
            is module_catalog_service
            and (
                organization_query is None
                or platform_runtime_application_service.organization_query
                is organization_query
            )
            and (
                tenant_context_service is None
                or platform_runtime_application_service.tenant_context_service
                is tenant_context_service
            )
            and (
                user_session is None
                or platform_runtime_application_service.user_session is user_session
            )
        )
    ):
        return platform_runtime_application_service

    if isinstance(module_catalog_service, ModuleCatalogQueryHandler):
        return PlatformRuntimeApplicationService(
            module_catalog_service=module_catalog_service,
            organization_query=organization_query,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
        )
    return platform_runtime_application_service


__all__ = [
    "PlatformRuntimeApplicationService",
    "PlatformRuntimeContextSnapshot",
    "resolve_platform_runtime_application_service",
]
