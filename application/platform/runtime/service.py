from __future__ import annotations

from dataclasses import dataclass

from core.platform.modules.runtime import (
    ModuleRuntimeService,
    ModuleRuntimeSnapshot,
    resolve_module_runtime_service,
)
from core.platform.org import Organization, OrganizationService


@dataclass(frozen=True)
class PlatformRuntimeContextSnapshot:
    context_label: str
    module_snapshot: ModuleRuntimeSnapshot


class PlatformRuntimeApplicationService:
    """Application-facing seam for active platform runtime context.

    Desktop UI can use this directly today. Future HTTP APIs can expose the
    same orchestration contract without depending on shell-specific code or on
    lower-level runtime/catalog services directly.
    """

    def __init__(
        self,
        *,
        module_runtime_service: ModuleRuntimeService,
        organization_service: OrganizationService | None = None,
    ) -> None:
        self._module_runtime_service = module_runtime_service
        self._organization_service = organization_service

    @property
    def module_runtime_service(self) -> ModuleRuntimeService:
        return self._module_runtime_service

    @property
    def organization_service(self) -> OrganizationService | None:
        return self._organization_service

    def list_modules(self):
        return self._module_runtime_service.list_modules()

    def list_platform_capabilities(self):
        return self._module_runtime_service.list_platform_capabilities()

    def list_entitlements(self):
        return self._module_runtime_service.list_entitlements()

    def list_licensed_modules(self):
        return self._module_runtime_service.list_licensed_modules()

    def list_enabled_modules(self):
        return self._module_runtime_service.list_enabled_modules()

    def list_available_modules(self):
        return self._module_runtime_service.list_available_modules()

    def list_planned_modules(self):
        return self._module_runtime_service.list_planned_modules()

    def enabled_capability_codes(self) -> tuple[str, ...]:
        return self._module_runtime_service.enabled_capability_codes()

    def is_licensed(self, module_code: str) -> bool:
        return self._module_runtime_service.is_licensed(module_code)

    def is_enabled(self, module_code: str) -> bool:
        return self._module_runtime_service.is_enabled(module_code)

    def get_entitlement(self, module_code: str):
        return self._module_runtime_service.get_entitlement(module_code)

    def set_module_state(
        self,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
    ):
        return self._module_runtime_service.set_module_state(
            module_code,
            licensed=licensed,
            enabled=enabled,
        )

    def shell_summary(self) -> str:
        return self._module_runtime_service.shell_summary()

    def current_context_label(self) -> str:
        return self._module_runtime_service.current_context_label()

    def snapshot(self) -> PlatformRuntimeContextSnapshot:
        module_snapshot = self._module_runtime_service.snapshot()
        return PlatformRuntimeContextSnapshot(
            context_label=module_snapshot.context_label,
            module_snapshot=module_snapshot,
        )

    def list_organizations(self, *, active_only: bool | None = None) -> list[Organization]:
        if self._organization_service is None:
            return []
        return self._organization_service.list_organizations(active_only=active_only)

    def get_active_organization(self) -> Organization | None:
        if self._organization_service is None:
            return None
        return self._organization_service.get_active_organization()

    def set_active_organization(self, organization_id: str) -> Organization:
        if self._organization_service is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_service.set_active_organization(organization_id)


def resolve_platform_runtime_application_service(
    *,
    platform_runtime_application_service: object | None,
    module_runtime_service: object | None,
    module_catalog_service=None,
    organization_service: OrganizationService | None = None,
) -> object | None:
    if isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
        runtime = resolve_module_runtime_service(
            module_runtime_service=module_runtime_service,
            module_catalog_service=module_catalog_service,
        )
        if (
            runtime is None
            or platform_runtime_application_service.module_runtime_service is runtime
        ):
            return platform_runtime_application_service

    runtime = resolve_module_runtime_service(
        module_runtime_service=module_runtime_service,
        module_catalog_service=module_catalog_service,
    )
    if isinstance(runtime, ModuleRuntimeService):
        return PlatformRuntimeApplicationService(
            module_runtime_service=runtime,
            organization_service=organization_service,
        )
    return platform_runtime_application_service


__all__ = [
    "PlatformRuntimeApplicationService",
    "PlatformRuntimeContextSnapshot",
    "resolve_platform_runtime_application_service",
]
