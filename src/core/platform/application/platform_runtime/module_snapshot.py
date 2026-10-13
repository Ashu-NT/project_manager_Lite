from __future__ import annotations

from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.contract.use_cases.platform_runtime import (
    ModuleRuntimeSnapshot,
    RuntimeEntitlementFact,
    RuntimeModuleFact,
    RuntimePlatformCapabilityFact,
)
from src.core.platform.domain.tenant.modules import EnterpriseModule, ModuleEntitlement


def _module_fact(module: EnterpriseModule) -> RuntimeModuleFact:
    return RuntimeModuleFact(
        code=module.code,
        label=module.label,
        description=module.description,
        default_enabled=module.default_enabled,
        stage=module.stage,
        primary_capabilities=tuple(module.primary_capabilities),
    )


def _entitlement_fact(entitlement: ModuleEntitlement) -> RuntimeEntitlementFact:
    return RuntimeEntitlementFact(
        module=_module_fact(entitlement.module),
        code=entitlement.code,
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
    )


def build_module_runtime_snapshot(catalog_service: ModuleCatalogService) -> ModuleRuntimeSnapshot:
    return ModuleRuntimeSnapshot(
        platform_capabilities=tuple(
            RuntimePlatformCapabilityFact(
                code=capability.code,
                label=capability.label,
                description=capability.description,
                always_on=capability.always_on,
            )
            for capability in catalog_service.list_platform_capabilities()
        ),
        entitlements=tuple(
            _entitlement_fact(entitlement) for entitlement in catalog_service.list_entitlements()
        ),
        enabled_modules=tuple(
            _module_fact(module) for module in catalog_service.list_enabled_modules()
        ),
        licensed_modules=tuple(
            _module_fact(module) for module in catalog_service.list_licensed_modules()
        ),
        available_modules=tuple(
            _module_fact(module) for module in catalog_service.list_available_modules()
        ),
        planned_modules=tuple(
            _module_fact(module) for module in catalog_service.list_planned_modules()
        ),
        shell_summary=catalog_service.shell_summary(),
        context_label=catalog_service.current_context_label(),
    )
