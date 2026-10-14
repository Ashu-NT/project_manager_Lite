"""Read-only module catalog queries.

`ModuleCatalogQueryHandler` is the module-catalog read capability every consumer depends on:
the module guards (`SupportsModuleEntitlements`: `get_entitlement`/`is_enabled`), the
platform runtime snapshot, integrations and the QML navigation shell."""

from __future__ import annotations

import os

from src.core.platform.application.tenant.modules.module_catalog_context import (
    ModuleCatalogContext,
)
from src.core.platform.domain.tenant.modules.defaults import (
    DEFAULT_ENTERPRISE_MODULES,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.module_definition import (
    EnterpriseModule,
    PlatformCapability,
)
from src.core.platform.domain.tenant.modules.module_entitlement import (
    ModuleCatalogSnapshot,
    ModuleEntitlement,
)
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


class ModuleCatalogQueryHandler:
    def __init__(self, *, context: ModuleCatalogContext) -> None:
        self._context = context

    def bootstrap_defaults(self) -> None:
        self._context.ensure_context_defaults()

    def list_modules(self) -> list[EnterpriseModule]:
        return list(self._context.modules)

    def list_platform_capabilities(self) -> list[PlatformCapability]:
        return list(self._context.platform_capabilities)

    def list_entitlements(self) -> list[ModuleEntitlement]:
        context = self._context
        return self._entitlements_from_records(context.effective_records(context.fetch_snapshot()))

    def list_licensed_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes()
        return self._licensed_from_codes(licensed_codes)

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        _licensed_codes, enabled_codes = self._effective_codes()
        return self._enabled_from_codes(enabled_codes)

    def list_available_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes()
        return self._available_from_codes(licensed_codes)

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._context.modules if module.stage == "planned"]

    def enabled_capability_codes(self) -> tuple[str, ...]:
        capability_codes = {capability.code for capability in self._context.platform_capabilities}
        for module in self.list_enabled_modules():
            capability_codes.update(module.primary_capabilities)
        return tuple(sorted(capability_codes))

    def is_licensed(self, module_code: str) -> bool:
        licensed_codes, _enabled_codes = self._effective_codes()
        return normalize_module_code(module_code) in licensed_codes

    def is_enabled(self, module_code: str) -> bool:
        _licensed_codes, enabled_codes = self._effective_codes()
        return normalize_module_code(module_code) in enabled_codes

    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None:
        context = self._context
        target_code = normalize_module_code(module_code)
        for module in context.modules:
            if module.code == target_code:
                records = context.effective_records(context.fetch_snapshot())
                records_by_code = {record.module_code: record for record in records}
                return context.build_entitlement(module, records_by_code)
        return None

    def snapshot(self) -> ModuleCatalogSnapshot:
        licensed_codes, enabled_codes = self._effective_codes()
        return ModuleCatalogSnapshot(
            enabled_modules=tuple(self._enabled_from_codes(enabled_codes)),
            licensed_modules=tuple(self._licensed_from_codes(licensed_codes)),
            available_modules=tuple(self._available_from_codes(licensed_codes)),
            planned_modules=tuple(self.list_planned_modules()),
            context_label=self.current_context_label(),
        )

    def current_context_label(self) -> str:
        organization = self._context.current_organization()
        if organization is None:
            return "Install Profile"
        return organization.display_name

    def shell_summary(self) -> str:
        # One snapshot answers every question below -- licensed/enabled/
        # available code sets and the full per-module entitlement list all
        # derive from the same single fetch instead of each independently
        # re-querying (the confirmed 15-20-query N+1 this pilot closes).
        context = self._context
        records = context.effective_records(context.fetch_snapshot())
        licensed_codes, enabled_codes = context.codes_from_records(records)
        enabled_labels = ", ".join(module.label for module in self._enabled_from_codes(enabled_codes)) or "None"
        licensed_labels = ", ".join(module.label for module in self._licensed_from_codes(licensed_codes)) or "None"
        available_labels = ", ".join(module.label for module in self._available_from_codes(licensed_codes)) or "None"
        planned_labels = ", ".join(module.label for module in self.list_planned_modules()) or "None"
        lifecycle_alerts = ", ".join(
            f"{entitlement.label} ({entitlement.lifecycle_label})"
            for entitlement in self._entitlements_from_records(records)
            if entitlement.lifecycle_alert
        ) or "None"
        return (
            f"Enabled: {enabled_labels}. Licensed: {licensed_labels}. "
            f"Available: {available_labels}. Planned: {planned_labels}. "
            f"Lifecycle alerts: {lifecycle_alerts}."
        )

    # -- derivations ---------------------------------------------------------------------------

    def _effective_codes(self) -> tuple[set[str], set[str]]:
        return self._context.effective_codes(self._context.fetch_snapshot())

    def _entitlements_from_records(self, records: list[ModuleEntitlementRecord]) -> list[ModuleEntitlement]:
        records_by_code = {record.module_code: record for record in records}
        return [self._context.build_entitlement(module, records_by_code) for module in self._context.modules]

    def _licensed_from_codes(self, licensed_codes: set[str]) -> list[EnterpriseModule]:
        return [module for module in self._context.modules if module.code in licensed_codes]

    def _enabled_from_codes(self, enabled_codes: set[str]) -> list[EnterpriseModule]:
        return [module for module in self._context.modules if module.code in enabled_codes]

    def _available_from_codes(self, licensed_codes: set[str]) -> list[EnterpriseModule]:
        return [
            module
            for module in self._context.modules
            if module.stage != "planned" and module.code not in licensed_codes
        ]


def build_default_module_catalog(
    raw_enabled_modules: str | None = None,
    raw_licensed_modules: str | None = None,
) -> ModuleCatalogQueryHandler:
    """In-memory install-profile catalog (no persistence) resolved from explicit values or the
    PM_ENABLED_MODULES / PM_LICENSED_MODULES environment."""
    resolved_enabled_raw = (
        raw_enabled_modules if raw_enabled_modules is not None else os.getenv("PM_ENABLED_MODULES")
    )
    resolved_licensed_raw = (
        raw_licensed_modules
        if raw_licensed_modules is not None
        else (
            raw_enabled_modules
            if raw_enabled_modules is not None
            else (
                os.getenv("PM_LICENSED_MODULES")
                if os.getenv("PM_LICENSED_MODULES") is not None
                else resolved_enabled_raw
            )
        )
    )
    return ModuleCatalogQueryHandler(
        context=ModuleCatalogContext(
            modules=DEFAULT_ENTERPRISE_MODULES,
            enabled_codes=parse_enabled_module_codes(
                resolved_enabled_raw if resolved_enabled_raw is not None else resolved_licensed_raw
            ),
            licensed_codes=parse_licensed_module_codes(resolved_licensed_raw),
        )
    )


__all__ = ["ModuleCatalogQueryHandler", "build_default_module_catalog"]
