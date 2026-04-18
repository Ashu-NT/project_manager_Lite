from __future__ import annotations

from typing import Callable, TypeVar

from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.api.desktop.platform.models import (
    DesktopApiError,
    DesktopApiResult,
    ModuleDto,
    ModuleEntitlementDto,
    ModuleStatePatchCommand,
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
)
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService

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
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[OrganizationDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_organization(row)
                for row in self._platform_runtime_application_service.list_organizations(
                    active_only=active_only
                )
            )
        )

    def list_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        return self._execute(
            lambda: tuple(
                self._serialize_module(module)
                for module in self._platform_runtime_application_service.list_modules()
            )
        )

    def patch_module_state(
        self,
        command: ModuleStatePatchCommand,
    ) -> DesktopApiResult[ModuleEntitlementDto]:
        return self._execute(
            lambda: self._serialize_entitlement(
                self._platform_runtime_application_service.set_module_state(
                    command.module_code,
                    licensed=command.licensed,
                    enabled=command.enabled,
                    lifecycle_status=command.lifecycle_status,
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
                    is_active=command.is_active,
                    initial_module_codes=command.initial_module_codes,
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
                    is_active=command.is_active,
                    expected_version=command.expected_version,
                )
            )
        )

    def set_active_organization(self, organization_id: str) -> DesktopApiResult[OrganizationDto]:
        return self._execute(
            lambda: self._serialize_organization(
                self._platform_runtime_application_service.set_active_organization(organization_id)
            )
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
            is_active=organization.is_active,
            version=organization.version,
        )


__all__ = ["PlatformRuntimeDesktopApi"]
