from __future__ import annotations

from core.platform.common.exceptions import NotFoundError
from src.core.platform.modules.domain.defaults import default_lifecycle_status
from src.core.platform.modules.domain.module_codes import normalize_module_code
from src.core.platform.modules.domain.module_entitlement import (
    ModuleCatalogSnapshot,
    ModuleEntitlement,
)


class ModuleCatalogQueryMixin:
    def bootstrap_defaults(self) -> None:
        self._ensure_context_defaults()

    def list_modules(self) -> list:
        return list(self._modules)

    def list_platform_capabilities(self) -> list:
        return list(self._platform_capabilities)

    def list_entitlements(self) -> list[ModuleEntitlement]:
        return [self._build_entitlement(module) for module in self._modules]

    def list_licensed_modules(self) -> list:
        licensed_codes, _enabled_codes = self._effective_codes()
        return [module for module in self._modules if module.code in licensed_codes]

    def list_enabled_modules(self) -> list:
        _licensed_codes, enabled_codes = self._effective_codes()
        return [module for module in self._modules if module.code in enabled_codes]

    def list_available_modules(self) -> list:
        licensed_codes, _enabled_codes = self._effective_codes()
        return [
            module
            for module in self._modules
            if module.stage != "planned" and module.code not in licensed_codes
        ]

    def list_planned_modules(self) -> list:
        return [module for module in self._modules if module.stage == "planned"]

    def enabled_capability_codes(self) -> tuple[str, ...]:
        capability_codes = {capability.code for capability in self._platform_capabilities}
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
        target_code = normalize_module_code(module_code)
        for module in self._modules:
            if module.code == target_code:
                return self._build_entitlement(module)
        return None

    def snapshot(self) -> ModuleCatalogSnapshot:
        return ModuleCatalogSnapshot(
            enabled_modules=tuple(self.list_enabled_modules()),
            licensed_modules=tuple(self.list_licensed_modules()),
            available_modules=tuple(self.list_available_modules()),
            planned_modules=tuple(self.list_planned_modules()),
            context_label=self.current_context_label(),
        )

    def current_context_label(self) -> str:
        organization = self._current_organization()
        if organization is None:
            return "Install Profile"
        return organization.display_name

    def shell_summary(self) -> str:
        enabled_labels = ", ".join(module.label for module in self.list_enabled_modules()) or "None"
        licensed_labels = ", ".join(module.label for module in self.list_licensed_modules()) or "None"
        available_labels = ", ".join(module.label for module in self.list_available_modules()) or "None"
        planned_labels = ", ".join(module.label for module in self.list_planned_modules()) or "None"
        lifecycle_alerts = ", ".join(
            f"{entitlement.label} ({entitlement.lifecycle_label})"
            for entitlement in self.list_entitlements()
            if entitlement.lifecycle_alert
        ) or "None"
        return (
            f"Enabled: {enabled_labels}. Licensed: {licensed_labels}. "
            f"Available: {available_labels}. Planned: {planned_labels}. "
            f"Lifecycle alerts: {lifecycle_alerts}."
        )

    def _build_entitlement(self, module) -> ModuleEntitlement:
        records_by_code = {
            record.module_code: record
            for record in self._effective_records()
        }
        record = records_by_code.get(module.code)
        if record is None:
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

    def _require_module(self, module_code: str):
        target_code = normalize_module_code(module_code)
        for module in self._modules:
            if module.code == target_code:
                return module
        raise NotFoundError("Module not found.", code="MODULE_NOT_FOUND")

    def _normalize_selected_module_codes(self, module_codes) -> set[str]:
        normalized_codes = {
            normalize_module_code(code)
            for code in (module_codes or ())
            if str(code or "").strip()
        }
        for module_code in normalized_codes:
            self._require_module(module_code)
        return normalized_codes


__all__ = ["ModuleCatalogQueryMixin"]
