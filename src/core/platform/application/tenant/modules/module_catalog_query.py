from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.tenant.modules.defaults import default_lifecycle_status
from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.module_definition import EnterpriseModule
from src.core.platform.domain.tenant.modules.module_entitlement import (
    ModuleCatalogSnapshot,
    ModuleEntitlement,
)

if TYPE_CHECKING:
    from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


class ModuleCatalogQueryMixin:
    def bootstrap_defaults(self) -> None:
        self._ensure_context_defaults()

    def list_modules(self) -> list[EnterpriseModule]:
        return list(self._modules)

    def list_platform_capabilities(self) -> list:
        return list(self._platform_capabilities)

    def list_entitlements(self) -> list[ModuleEntitlement]:
        return self._entitlements_from_records(self._effective_records(self._fetch_snapshot()))

    def list_licensed_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes(self._fetch_snapshot())
        return self._licensed_from_codes(licensed_codes)

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        _licensed_codes, enabled_codes = self._effective_codes(self._fetch_snapshot())
        return self._enabled_from_codes(enabled_codes)

    def list_available_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes(self._fetch_snapshot())
        return self._available_from_codes(licensed_codes)

    def _entitlements_from_records(self, records: list["ModuleEntitlementRecord"]) -> list[ModuleEntitlement]:
        records_by_code = {record.module_code: record for record in records}
        return [self._build_entitlement(module, records_by_code) for module in self._modules]

    def _licensed_from_codes(self, licensed_codes: set[str]) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code in licensed_codes]

    def _enabled_from_codes(self, enabled_codes: set[str]) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code in enabled_codes]

    def _available_from_codes(self, licensed_codes: set[str]) -> list[EnterpriseModule]:
        return [
            module
            for module in self._modules
            if module.stage != "planned" and module.code not in licensed_codes
        ]

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.stage == "planned"]

    def enabled_capability_codes(self) -> tuple[str, ...]:
        capability_codes = {capability.code for capability in self._platform_capabilities}
        for module in self.list_enabled_modules():
            capability_codes.update(module.primary_capabilities)
        return tuple(sorted(capability_codes))

    def is_licensed(self, module_code: str) -> bool:
        licensed_codes, _enabled_codes = self._effective_codes(self._fetch_snapshot())
        return normalize_module_code(module_code) in licensed_codes

    def is_enabled(self, module_code: str) -> bool:
        _licensed_codes, enabled_codes = self._effective_codes(self._fetch_snapshot())
        return normalize_module_code(module_code) in enabled_codes

    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None:
        target_code = normalize_module_code(module_code)
        for module in self._modules:
            if module.code == target_code:
                records = self._effective_records(self._fetch_snapshot())
                records_by_code = {record.module_code: record for record in records}
                return self._build_entitlement(module, records_by_code)
        return None

    def snapshot(self) -> ModuleCatalogSnapshot:
        licensed_codes, enabled_codes = self._effective_codes(self._fetch_snapshot())
        return ModuleCatalogSnapshot(
            enabled_modules=tuple(self._enabled_from_codes(enabled_codes)),
            licensed_modules=tuple(self._licensed_from_codes(licensed_codes)),
            available_modules=tuple(self._available_from_codes(licensed_codes)),
            planned_modules=tuple(self.list_planned_modules()),
            context_label=self.current_context_label(),
        )

    def current_context_label(self) -> str:
        organization = self._current_organization()
        if organization is None:
            return "Install Profile"
        return organization.display_name

    def shell_summary(self) -> str:
        # One snapshot answers every question below -- licensed/enabled/
        # available code sets and the full per-module entitlement list all
        # derive from the same single fetch instead of each independently
        # re-querying (the confirmed 15-20-query N+1 this pilot closes).
        snapshot = self._fetch_snapshot()
        records = self._effective_records(snapshot)
        licensed_codes, enabled_codes = self._codes_from_records(records)
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

    def _build_entitlement(
        self, module: EnterpriseModule, records_by_code: dict[str, "ModuleEntitlementRecord"]
    ) -> ModuleEntitlement:
        record = records_by_code.get(module.code)
        missing_organization_context = (
            getattr(self, "_entitlement_repo", None) is not None
            and not getattr(self, "_has_active_organization_context", lambda: False)()
        )
        if record is None:
            if missing_organization_context:
                licensed = False
                enabled = False
                lifecycle_status = default_lifecycle_status(False)
            else:
                licensed = module.code in self._licensed_codes
                enabled = module.code in self._enabled_codes
                lifecycle_status = default_lifecycle_status(licensed)
        else:
            licensed = record.licensed
            enabled = record.enabled
            lifecycle_status = record.lifecycle_status
        return ModuleEntitlement(
            module=module,
            licensed=licensed,
            enabled=enabled,
            lifecycle_status=lifecycle_status,
        )

    def _require_module(self, module_code: str) -> EnterpriseModule:
        target_code = normalize_module_code(module_code)
        for module in self._modules:
            if module.code == target_code:
                return module
        raise NotFoundError("Module not found.", code="MODULE_NOT_FOUND")

    def _normalize_selected_module_codes(self, module_codes: object) -> set[str]:
        normalized_codes = {
            normalize_module_code(code)
            for code in (module_codes or ())
            if str(code or "").strip()
        }
        for module_code in normalized_codes:
            self._require_module(module_code)
        return normalized_codes


__all__ = ["ModuleCatalogQueryMixin"]
