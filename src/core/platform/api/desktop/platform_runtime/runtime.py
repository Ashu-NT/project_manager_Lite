from __future__ import annotations

from typing import Callable, TypeVar

from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationCatalogPageDto,
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationStatisticsDto,
    OrganizationUpdateCommand,
)
from src.core.platform.api.desktop.platform_runtime.models.runtime import (
    CountryDto,
    ModuleDto,
    ModuleEntitlementDto,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
    TimezoneDto,
)
from src.core.platform.application.platform_runtime import PlatformRuntimeApplicationService
from src.core.shared.reference_data import COUNTRY_OPTIONS, TIMEZONE_OPTIONS

_ResultT = TypeVar("_ResultT")


class PlatformRuntimeDesktopApi:
    """Desktop-facing adapter for platform runtime and organization flows."""

    def __init__(
        self,
        *,
        platform_runtime_application_service: PlatformRuntimeApplicationService,
    ) -> None:
        self._platform_runtime_application_service = platform_runtime_application_service

    def get_runtime_context(self) -> DesktopApiResult[PlatformRuntimeContextDto]:
        return self._execute(
            lambda: self._build_runtime_context(),
        )

    def list_organizations(
        self,
        *,
        enabled_only: bool | None = None,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._platform_runtime_application_service.list_organizations(
                    enabled_only=enabled_only
                )
            )
        )

    def list_organizations_page(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        enabled_only: bool | None = None,
    ) -> DesktopApiResult[OrganizationCatalogPageDto]:
        return self._execute(
            lambda: self._build_organizations_page(
                page=page, page_size=page_size, search=search, enabled_only=enabled_only
            )
        )

    def get_organization_statistics(self, organization_id: str) -> DesktopApiResult[OrganizationStatisticsDto]:
        return self._execute(
            lambda: self._serialize_organization_statistics(
                self._platform_runtime_application_service.get_organization_statistics(organization_id)
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
            lambda: self._platform_runtime_application_service.get_organization_count()
        )

    def get_current_permissions(self) -> DesktopApiResult[tuple[str, ...]]:
        return self._execute(
            lambda: tuple(sorted(self._platform_runtime_application_service.get_current_permissions()))
        )

    def list_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_module(module)
                for module in self._platform_runtime_application_service.list_modules()
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
                for module in self._platform_runtime_application_service.list_accessible_modules()
            )
        )

    def license_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.license_module(module_code)
            )
        )

    def revoke_module_license(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.revoke_module_license(module_code)
            )
        )

    def license_module_for_organization(
        self, organization_id: str, module_code: str
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.license_module_for_organization(
                    organization_id, module_code
                )
            )
        )

    def revoke_module_license_for_organization(
        self, organization_id: str, module_code: str
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.revoke_module_license_for_organization(
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
                for entitlement in self._platform_runtime_application_service.bulk_set_module_license(
                    organization_module_pairs, licensed=licensed
                )
            )
        )

    def enable_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.enable_module(module_code)
            )
        )

    def disable_module(self, module_code: str) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.disable_module(module_code)
            )
        )

    def transition_module_lifecycle(
        self,
        module_code: str,
        lifecycle_status: str,
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.transition_module_lifecycle(
                    module_code, lifecycle_status
                )
            )
        )

    def provision_organization(
        self,
        command: OrganizationProvisionCommand,
    ) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._platform_runtime_application_service.provision_organization(
                    organization_code=command.organization_code,
                    display_name=command.display_name,
                    timezone_name=command.timezone_name,
                    base_currency=command.base_currency,
                    is_enabled=command.is_enabled,
                    initial_module_codes=command.initial_module_codes,
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
            )
        )

    def update_organization(
        self,
        command: OrganizationUpdateCommand,
    ) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._platform_runtime_application_service.update_organization(
                    command.organization_id,
                    organization_code=command.organization_code,
                    display_name=command.display_name,
                    timezone_name=command.timezone_name,
                    base_currency=command.base_currency,
                    is_enabled=command.is_enabled,
                    expected_version=command.expected_version,
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
            )
        )

    def enable_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._platform_runtime_application_service.enable_organization(organization_id)
            )
        )

    def disable_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._platform_runtime_application_service.disable_organization(organization_id)
            )
        )

    def bulk_set_organization_enabled(
        self, organization_ids: tuple[str, ...], *, is_enabled: bool
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._platform_runtime_application_service.bulk_set_organization_enabled(
                    organization_ids, is_enabled=is_enabled
                )
            )
        )

    def bulk_update_organization_currency(
        self, organization_ids: tuple[str, ...], base_currency: str
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._platform_runtime_application_service.bulk_update_organization_currency(
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
                for row in self._platform_runtime_application_service.bulk_update_organization_timezone(
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
        enabled_only: bool | None,
    ) -> OrganizationCatalogPageDto:
        organization_page = self._platform_runtime_application_service.list_organizations_page(
            page=page, page_size=page_size, search=search, enabled_only=enabled_only
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

    def _build_runtime_context(self) -> PlatformRuntimeContextDto:
        snapshot = self._platform_runtime_application_service.snapshot()
        active_organization = self._platform_runtime_application_service.get_active_organization()
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
            is_enabled=organization.is_enabled,
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
