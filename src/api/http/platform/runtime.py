from __future__ import annotations

from typing import Any, Callable, TypeVar

from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.api.http.platform.models import (
    HttpApiResponse,
    ModuleStatePatchRequest,
    OrganizationProvisionRequest,
)
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService

_ResultT = TypeVar("_ResultT")


class PlatformRuntimeHttpApi:
    """Transport-facing adapter for module licensing and organization setup."""

    def __init__(
        self,
        *,
        platform_runtime_application_service: PlatformRuntimeApplicationService,
    ) -> None:
        self._platform_runtime_application_service = platform_runtime_application_service

    def get_runtime_context(self) -> HttpApiResponse:
        snapshot = self._platform_runtime_application_service.snapshot()
        active_organization = self._platform_runtime_application_service.get_active_organization()
        return HttpApiResponse(
            status_code=200,
            body={
                "context_label": snapshot.context_label,
                "shell_summary": snapshot.module_snapshot.shell_summary,
                "active_organization": self._serialize_organization(active_organization)
                if active_organization is not None
                else None,
                "platform_capabilities": [
                    self._serialize_platform_capability(capability)
                    for capability in snapshot.module_snapshot.platform_capabilities
                ],
                "entitlements": [
                    self._serialize_entitlement(entitlement)
                    for entitlement in snapshot.module_snapshot.entitlements
                ],
                "enabled_modules": [
                    self._serialize_module(module)
                    for module in snapshot.module_snapshot.enabled_modules
                ],
                "licensed_modules": [
                    self._serialize_module(module)
                    for module in snapshot.module_snapshot.licensed_modules
                ],
                "available_modules": [
                    self._serialize_module(module)
                    for module in snapshot.module_snapshot.available_modules
                ],
                "planned_modules": [
                    self._serialize_module(module)
                    for module in snapshot.module_snapshot.planned_modules
                ],
            },
        )

    def list_organizations(self, *, active_only: bool | None = None) -> HttpApiResponse:
        return self._execute(
            lambda: self._platform_runtime_application_service.list_organizations(active_only=active_only),
            serializer=lambda rows: [self._serialize_organization(row) for row in rows],
        )

    def patch_module_state(self, request: ModuleStatePatchRequest) -> HttpApiResponse:
        return self._execute(
            lambda: self._platform_runtime_application_service.set_module_state(
                request.module_code,
                licensed=request.licensed,
                enabled=request.enabled,
                lifecycle_status=request.lifecycle_status,
            ),
            serializer=self._serialize_entitlement,
        )

    def provision_organization(self, request: OrganizationProvisionRequest) -> HttpApiResponse:
        return self._execute(
            lambda: self._platform_runtime_application_service.provision_organization(
                organization_code=request.organization_code,
                display_name=request.display_name,
                timezone_name=request.timezone_name,
                base_currency=request.base_currency,
                is_active=request.is_active,
                initial_module_codes=request.initial_module_codes,
            ),
            serializer=self._serialize_organization,
            success_status=201,
        )

    def _execute(
        self,
        operation: Callable[[], _ResultT],
        *,
        serializer: Callable[[_ResultT], Any],
        success_status: int = 200,
    ) -> HttpApiResponse:
        try:
            result = operation()
        except DomainError as exc:
            return self._error_response(exc)
        return HttpApiResponse(
            status_code=success_status,
            body={"data": serializer(result)},
        )

    def _error_response(self, exc: DomainError) -> HttpApiResponse:
        if isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, ValidationError):
            status_code = 422
        elif isinstance(exc, (BusinessRuleError, ConcurrencyError)):
            status_code = 409
        else:
            status_code = 400
        return HttpApiResponse(
            status_code=status_code,
            body={
                "error": {
                    "code": getattr(exc, "code", exc.__class__.__name__),
                    "message": str(exc),
                }
            },
        )

    @staticmethod
    def _serialize_platform_capability(capability) -> dict[str, Any]:
        return {
            "code": capability.code,
            "label": capability.label,
            "description": capability.description,
            "always_on": capability.always_on,
        }

    @staticmethod
    def _serialize_module(module) -> dict[str, Any]:
        return {
            "code": module.code,
            "label": module.label,
            "description": module.description,
            "default_enabled": module.default_enabled,
            "stage": module.stage,
            "primary_capabilities": list(module.primary_capabilities),
        }

    def _serialize_entitlement(self, entitlement) -> dict[str, Any]:
        return {
            "module_code": entitlement.code,
            "label": entitlement.label,
            "stage": entitlement.stage,
            "licensed": entitlement.licensed,
            "enabled": entitlement.enabled,
            "runtime_enabled": entitlement.runtime_enabled,
            "lifecycle_status": entitlement.lifecycle_status,
            "lifecycle_label": entitlement.lifecycle_label,
            "lifecycle_alert": entitlement.lifecycle_alert,
            "available_to_license": entitlement.available_to_license,
            "planned": entitlement.planned,
            "module": self._serialize_module(entitlement.module),
        }

    @staticmethod
    def _serialize_organization(organization) -> dict[str, Any]:
        return {
            "id": organization.id,
            "organization_code": organization.organization_code,
            "display_name": organization.display_name,
            "timezone_name": organization.timezone_name,
            "base_currency": organization.base_currency,
            "is_active": organization.is_active,
            "version": organization.version,
        }


__all__ = ["PlatformRuntimeHttpApi"]
