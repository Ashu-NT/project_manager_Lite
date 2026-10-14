from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationCalendarSummaryDto,
    OrganizationCatalogPageDto,
    OrganizationDto,
    OrganizationStatisticsDto,
)
from src.core.platform.api.desktop.models.common import (
    DesktopApiError,
    DesktopApiResult,
)
from src.core.platform.api.desktop.platform_runtime.models.runtime import (
    CountryDto,
    ModuleDto,
    ModuleEntitlementDto,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
    TimezoneDto,
)
from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationProvisioningCommandHandler,
    OrganizationQueryHandler,
)
from src.core.platform.application.master_data.org.dto import (
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeQueryHandler,
)
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementCommandHandler,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.reference_data import COUNTRY_OPTIONS, TIMEZONE_OPTIONS

_ResultT = TypeVar("_ResultT")


class PlatformRuntimeDesktopApi:
    """Desktop-facing adapter for platform runtime and organization flows."""

    def __init__(
        self,
        *,
        platform_runtime_query: PlatformRuntimeQueryHandler,
        module_catalog_service: ModuleCatalogQueryHandler,
        organization_query: OrganizationQueryHandler,
        organization_commands: OrganizationCommandHandler,
        organization_lifecycle: OrganizationLifecycleCommandHandler,
        organization_provisioning_commands: OrganizationProvisioningCommandHandler,
        tenant_context_service: TenantContextService,
        module_entitlement_commands: ModuleEntitlementCommandHandler,
    ) -> None:
        self._platform_runtime_query = platform_runtime_query
        self._module_catalog_service = module_catalog_service
        self._organization_query = organization_query
        self._organization_commands = organization_commands
        self._organization_lifecycle = organization_lifecycle
        self._organization_provisioning_commands = organization_provisioning_commands
        self._tenant_context_service = tenant_context_service
        self._module_entitlement_commands = module_entitlement_commands

    def get_runtime_context(self) -> DesktopApiResult[PlatformRuntimeContextDto]:
        return self._execute(
            lambda: self._build_runtime_context(),
        )

    def list_organizations(
        self,
        *,
        status: str | None = None,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_query.list_organizations(
                    status=status
                )
            )
        )

    def list_organizations_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        status: str | None = None,
    ) -> DesktopApiResult[OrganizationCatalogPageDto]:
        return self._execute(
            lambda: self._build_organizations_page(
                page=page, page_size=page_size, search=search, status=status
            )
        )

    def get_organization_statistics(self, organization_id: str) -> DesktopApiResult[OrganizationStatisticsDto]:
        return self._execute(
            lambda: self._serialize_organization_statistics(
                self._organization_query.get_organization_statistics(organization_id)
            )
        )

    def get_organization_calendar_summary(
        self, organization_id: str
    ) -> DesktopApiResult[OrganizationCalendarSummaryDto]:
        return self._execute(
            lambda: self._serialize_organization_calendar_summary(
                self._organization_query.get_organization_calendar_summary(organization_id)
            )
        )

    def list_countries(self) -> DesktopApiResult[tuple[CountryDto, ...]]:
        """Static ISO 3166-1 reference data for the Organization registered-address
        country picker -- no session/tenant scoping needed, never persisted."""
        return self._execute(
            lambda: tuple(CountryDto(code=code, name=name) for code, name in COUNTRY_OPTIONS)
        )

    def list_timezones(self) -> DesktopApiResult[tuple[TimezoneDto, ...]]:
        """Static IANA time zone reference data for the Organization timezone
        picker -- no session/tenant scoping needed, never persisted."""
        return self._execute(
            lambda: tuple(TimezoneDto(name=name) for name, _label in TIMEZONE_OPTIONS)
        )

    def get_organization_count(self) -> DesktopApiResult[int]:
        return self._execute(
            lambda: self._organization_query.get_organization_count()
        )

    def get_current_permissions(self) -> DesktopApiResult[tuple[str, ...]]:
        return self._execute(
            lambda: tuple(sorted(self._platform_runtime_query.get_current_permissions()))
        )

    def list_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_module(module)
                for module in self._module_catalog_service.list_modules()
            )
        )

    def list_accessible_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        """Enabled modules the current user also has permission to use -- the
        same single authoritative definition Global Overview's module cards
        and Quick Actions already read (see module_access_policy.py). Shell
        navigation consumes this instead of keeping its own copy."""
        return self._execute(
            lambda: tuple(
                self._serialize_module(module)
                for module in self._platform_runtime_query.list_accessible_modules()
            )
        )

    def license_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.license_module(
                    self._require_active_organization_id(), module_code
                )
            )
        )

    def revoke_module_license(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.revoke_module_license(
                    self._require_active_organization_id(), module_code
                )
            )
        )

    def license_module_for_organization(
        self, organization_id: str, module_code: str
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.license_module(organization_id, module_code)
            )
        )

    def revoke_module_license_for_organization(
        self, organization_id: str, module_code: str
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.revoke_module_license(
                    organization_id, module_code
                )
            )
        )

    def bulk_set_module_license(
        self, organization_module_pairs: tuple[tuple[str, str], ...], *, licensed: bool
    ) -> DesktopApiResult[tuple[ModuleEntitlementDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_entitlement(entitlement)
                for entitlement in self._module_entitlement_commands.bulk_set_module_license(
                    organization_module_pairs, licensed=licensed
                )
            )
        )

    def enable_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.enable_module(
                    self._require_active_organization_id(), module_code
                )
            )
        )

    def disable_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.disable_module(
                    self._require_active_organization_id(), module_code
                )
            )
        )

    def transition_module_lifecycle(
        self,
        module_code: str,
        lifecycle_status: str,
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._module_entitlement_commands.transition_module_lifecycle(
                    self._require_active_organization_id(), module_code, lifecycle_status
                )
            )
        )

    def _require_active_organization_id(self) -> str:
        """Active-organization module commands act on the caller's selected organization;
        the `*_for_organization` variants take an explicit organization instead."""
        active_organization = self._tenant_context_service.get_active_organization()
        if active_organization is None:
            raise RuntimeError("Active organization is required to manage module entitlements.")
        return active_organization.id

    def provision_organization(
        self,
        command: OrganizationProvisionCommand,
    ) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._organization_provisioning_commands.provision_organization(command)
            )
        )

    def update_organization(
        self,
        command: OrganizationUpdateCommand,
    ) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._organization_commands.update_organization(command)
            )
        )

    def activate_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._organization_lifecycle.activate_organization(organization_id)
            )
        )

    def deactivate_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._organization_lifecycle.deactivate_organization(organization_id)
            )
        )

    def archive_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._organization_lifecycle.archive_organization(organization_id)
            )
        )

    def bulk_activate_organizations(
        self, organization_ids: tuple[str, ...]
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_lifecycle.bulk_activate_organizations(
                    organization_ids
                )
            )
        )

    def bulk_deactivate_organizations(
        self, organization_ids: tuple[str, ...]
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_lifecycle.bulk_deactivate_organizations(
                    organization_ids
                )
            )
        )

    def bulk_archive_organizations(
        self, organization_ids: tuple[str, ...]
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_lifecycle.bulk_archive_organizations(
                    organization_ids
                )
            )
        )

    def bulk_update_organization_currency(
        self, organization_ids: tuple[str, ...], base_currency: str
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_commands.bulk_update_organization_currency(
                    organization_ids, base_currency
                )
            )
        )

    def bulk_update_organization_timezone(
        self, organization_ids: tuple[str, ...], timezone_name: str
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._organization_commands.bulk_update_organization_timezone(
                    organization_ids, timezone_name
                )
            )
        )

    def _build_organizations_page(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
    ) -> OrganizationCatalogPageDto:
        organization_page = self._organization_query.list_organizations_page(
            page=page, page_size=page_size, search=search, status=status
        )
        return OrganizationCatalogPageDto(
            items=tuple(self._serialize_organization(row) for row in organization_page.items),
            total=organization_page.total,
            filtered_total=organization_page.filtered_total,
            page=organization_page.page,
            page_size=organization_page.page_size,
        )

    @staticmethod
    def _serialize_organization_statistics(statistics) -> OrganizationStatisticsDto:
        return OrganizationStatisticsDto(
            site_count=statistics.site_count,
            department_count=statistics.department_count,
            employee_count=statistics.employee_count,
            document_count=statistics.document_count,
        )

    @staticmethod
    def _serialize_organization_calendar_summary(summary) -> OrganizationCalendarSummaryDto:
        return OrganizationCalendarSummaryDto(
            has_calendar=summary.has_calendar,
            calendar_id=summary.calendar_id,
            calendar_name=summary.calendar_name,
            timezone=summary.timezone,
            locale=summary.locale or "",
            working_weekdays=summary.working_weekdays,
            holiday_count=summary.holiday_count,
        )

    def _build_runtime_context(self) -> PlatformRuntimeContextDto:
        snapshot = self._platform_runtime_query.snapshot()
        active_organization = self._tenant_context_service.get_active_organization()
        return PlatformRuntimeContextDto(
            context_label=snapshot.context_label,
            shell_summary=snapshot.module_snapshot.shell_summary,
            active_organization=self._serialize_organization(active_organization)
            if active_organization is not None
            else None,
            platform_capabilities=tuple(
                self._serialize_platform_capability(capability)
                for capability in snapshot.module_snapshot.platform_capabilities
            ),
            entitlements=tuple(
                self._serialize_entitlement(entitlement)
                for entitlement in snapshot.module_snapshot.entitlements
            ),
            enabled_modules=tuple(
                self._serialize_module(module)
                for module in snapshot.module_snapshot.enabled_modules
            ),
            licensed_modules=tuple(
                self._serialize_module(module)
                for module in snapshot.module_snapshot.licensed_modules
            ),
            available_modules=tuple(
                self._serialize_module(module)
                for module in snapshot.module_snapshot.available_modules
            ),
            planned_modules=tuple(
                self._serialize_module(module)
                for module in snapshot.module_snapshot.planned_modules
            ),
        )

    def _execute(self, operation: Callable[[], _ResultT]) -> DesktopApiResult[_ResultT]:
        try:
            return DesktopApiResult(ok=True, data=operation())
        except DomainError as exc:
            return DesktopApiResult(ok=False, error=self._serialize_error(exc))

    @staticmethod
    def _serialize_error(exc: DomainError) -> DesktopApiError:
        if isinstance(exc, NotFoundError):
            category = "not_found"
        elif isinstance(exc, ValidationError):
            category = "validation"
        elif isinstance(exc, (BusinessRuleError, ConcurrencyError)):
            category = "conflict"
        else:
            category = "domain"
        return DesktopApiError(
            code=getattr(exc, "code", exc.__class__.__name__),
            message=str(exc),
            category=category,
        )

    @staticmethod
    def _serialize_platform_capability(capability) -> PlatformCapabilityDto:
        return PlatformCapabilityDto(
            code=capability.code,
            label=capability.label,
            description=capability.description,
            always_on=capability.always_on,
        )

    @staticmethod
    def _serialize_module(module) -> ModuleDto:
        return ModuleDto(
            code=module.code,
            label=module.label,
            description=module.description,
            default_enabled=module.default_enabled,
            stage=module.stage,
            primary_capabilities=tuple(module.primary_capabilities),
        )

    def _serialize_entitlement(self, entitlement) -> ModuleEntitlementDto:
        return ModuleEntitlementDto(
            module_code=entitlement.code,
            label=entitlement.label,
            stage=entitlement.stage,
            licensed=entitlement.licensed,
            enabled=entitlement.enabled,
            runtime_enabled=entitlement.runtime_enabled,
            lifecycle_status=entitlement.lifecycle_status,
            lifecycle_label=entitlement.lifecycle_label,
            lifecycle_alert=entitlement.lifecycle_alert,
            available_to_license=entitlement.available_to_license,
            planned=entitlement.planned,
            module=self._serialize_module(entitlement.module),
        )

    @staticmethod
    def _serialize_organization(organization) -> OrganizationDto:
        return OrganizationDto(
            id=organization.id,
            organization_code=organization.organization_code,
            display_name=organization.display_name,
            timezone_name=organization.timezone_name,
            base_currency=organization.base_currency,
            status=organization.status,
            version=organization.version,
            legal_name=organization.legal_name,
            registration_number=organization.registration_number,
            tax_id=organization.tax_id,
            address_line_1=organization.address_line_1,
            address_line_2=organization.address_line_2,
            postal_code=organization.postal_code,
            city=organization.city,
            state_region=organization.state_region,
            country_code=organization.country_code,
            email=organization.email,
            phone=organization.phone,
            website=organization.website,
        )


__all__ = ["PlatformRuntimeDesktopApi"]
