"""ModuleRegistry — capability-aware entitlement facade.

Wraps ModuleCatalogService and adds fine-grained capability checks and
integration-pairing rules. All other layers (API, controllers, QML) should
query ModuleRegistry, not import optional module code directly.

Module IDs match DEFAULT_ENTERPRISE_MODULES codes:
    platform             (always enabled — built-in)
    project_management
    qhse
    hr_management
"""

from __future__ import annotations

from src.core.platform.application.tenant.modules import ModuleCatalogService

# Maps capability_id → module_id.  "platform" capabilities are always available.
_CAPABILITY_MODULE: dict[str, str] = {
    # Platform (always on)
    "platform.sites.read": "platform",
    "platform.parties.read": "platform",
    "platform.employees.read": "platform",
    "platform.documents.attach": "platform",
    "platform.approvals.create": "platform",
    "platform.audit.write": "platform",
    # Project Management
    "project_management.projects.read": "project_management",
    "project_management.tasks.read": "project_management",
    "project_management.resources.read": "project_management",
    "project_management.financials.read": "project_management",
}

# Maps capability_id → short labels of modules that consume the capability.
_CAPABILITY_CONSUMERS: dict[str, list[str]] = {
    "platform.sites.read":              ["PM"],
    "platform.parties.read":            ["PM"],
    "platform.employees.read":          ["PM"],
    "platform.documents.attach":        ["PM"],
    "platform.approvals.create":        ["PM"],
    "platform.audit.write":             ["PM"],
    "project_management.projects.read": ["PM"],
    "project_management.tasks.read":    ["PM"],
    "project_management.resources.read": ["PM"],
    "project_management.financials.read": ["PM"],
}

_MODULE_LABELS: dict[str, str] = {
    "platform":              "Platform",
    "project_management":    "PM",
    "qhse":                  "QHSE",
    "hr_management":         "HR",
}

# Maps (source_module, target_module, capability) → bool (static rules).
# Dynamic check also requires both modules to be enabled at runtime.
_INTEGRATION_RULES: frozenset[tuple[str, str, str]] = frozenset(set())


class ModuleRegistry:
    """Central entitlement + capability gateway.

    Inject this into API classes and controllers.  Never import optional module
    code at the call site — use this registry to guard every cross-module action.
    """

    def __init__(self, module_catalog_service: ModuleCatalogService) -> None:
        self._runtime = module_catalog_service

    # ------------------------------------------------------------------
    # Module-level checks
    # ------------------------------------------------------------------

    def is_module_enabled(self, module_id: str) -> bool:
        if module_id == "platform":
            return True
        return self._runtime.is_enabled(module_id)

    def get_module_status(self, module_id: str) -> str:
        if module_id == "platform":
            return "active"
        entitlement = self._runtime.get_entitlement(module_id)
        return entitlement.lifecycle_status if entitlement else "unknown"

    # ------------------------------------------------------------------
    # Capability-level checks
    # ------------------------------------------------------------------

    def has_capability(self, capability_id: str) -> bool:
        module_id = _CAPABILITY_MODULE.get(capability_id)
        if module_id is None:
            return False
        return self.is_module_enabled(module_id)

    # ------------------------------------------------------------------
    # Cross-module reference checks
    # ------------------------------------------------------------------

    def can_open_reference(self, module_id: str, entity_type: str) -> bool:  # noqa: ARG002
        return self.is_module_enabled(module_id)

    def can_create_reference(self, module_id: str, entity_type: str) -> bool:  # noqa: ARG002
        return self.is_module_enabled(module_id)

    def can_use_integration(
        self,
        source_module: str,
        target_module: str,
        capability: str,
    ) -> bool:
        rule_key = (source_module, target_module, capability)
        if rule_key not in _INTEGRATION_RULES:
            return False
        return self.is_module_enabled(source_module) and self.is_module_enabled(target_module)

    # ------------------------------------------------------------------
    # Convenience snapshot for QML / controllers
    # ------------------------------------------------------------------

    def list_capabilities(self) -> list[dict]:
        """Return structured capability rows for admin/settings display."""
        rows: list[dict] = []
        for cap_id, module_id in sorted(_CAPABILITY_MODULE.items()):
            enabled = self.is_module_enabled(module_id)
            consumers = _CAPABILITY_CONSUMERS.get(cap_id, [])
            provider_label = _MODULE_LABELS.get(module_id, module_id)
            rows.append({
                "id": cap_id,
                "title": cap_id,
                "subtitle": provider_label,
                "statusLabel": "Active" if enabled else "Inactive",
                "metaText": ", ".join(consumers) if consumers else "—",
            })
        return rows

    def capability_snapshot(self) -> dict[str, bool]:
        """Return a flat dict of all known integration capabilities for QML binding."""
        return {
            "isPlatformEnabled": True,
            "isProjectManagementEnabled": self.is_module_enabled("project_management"),
            "isInventoryProcurementEnabled": self.is_module_enabled("inventory_procurement"),
            "isQhseEnabled": self.is_module_enabled("qhse"),
            "isHrManagementEnabled": self.is_module_enabled("hr_management"),
            # Cross-module integration pairs
            "canPmLinkInventory": self.can_use_integration(
                "project_management", "inventory_procurement", "material_demand"
            ),
            "canInventoryLinkPm": self.can_use_integration(
                "inventory_procurement", "project_management", "source_reference"
            ),
        }


__all__ = ["ModuleRegistry"]
