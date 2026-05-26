"""ModuleRegistry — capability-aware entitlement facade.

Wraps ModuleRuntimeService and adds fine-grained capability checks and
integration-pairing rules. All other layers (API, controllers, QML) should
query ModuleRegistry, not import optional module code directly.

Module IDs match DEFAULT_ENTERPRISE_MODULES codes:
    platform             (always enabled — built-in)
    project_management
    inventory_procurement
    maintenance_management
    qhse
    hr_management
"""

from __future__ import annotations

from src.application.runtime.entitlement_runtime import ModuleRuntimeService

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
    "project_management.tasks.open": "project_management",
    "project_management.material_demand.create": "project_management",
    "project_management.resources.read": "project_management",
    "project_management.financials.read": "project_management",
    # Inventory / Procurement
    "inventory.stock.read": "inventory_procurement",
    "inventory.reservations.create": "inventory_procurement",
    "inventory.reservations.read": "inventory_procurement",
    "procurement.requisitions.create": "inventory_procurement",
    "procurement.purchase_orders.read": "inventory_procurement",
    "procurement.purchase_orders.create": "inventory_procurement",
    # Maintenance
    "maintenance.work_orders.read": "maintenance_management",
    "maintenance.work_orders.open": "maintenance_management",
    "maintenance.material_demand.create": "maintenance_management",
    "maintenance.assets.read": "maintenance_management",
}

# Maps capability_id → short labels of modules that consume the capability.
_CAPABILITY_CONSUMERS: dict[str, list[str]] = {
    "platform.sites.read":              ["PM", "INV", "MNT"],
    "platform.parties.read":            ["PM", "INV", "MNT"],
    "platform.employees.read":          ["PM", "MNT"],
    "platform.documents.attach":        ["PM", "INV", "MNT"],
    "platform.approvals.create":        ["PM", "INV", "MNT"],
    "platform.audit.write":             ["PM", "INV", "MNT"],
    "project_management.projects.read": ["PM"],
    "project_management.tasks.read":    ["PM"],
    "project_management.tasks.open":    ["INV", "MNT"],
    "project_management.material_demand.create": ["PM"],
    "project_management.resources.read": ["PM"],
    "project_management.financials.read": ["PM"],
    "inventory.stock.read":             ["PM", "MNT"],
    "inventory.reservations.create":    ["PM", "MNT"],
    "inventory.reservations.read":      ["PM", "MNT"],
    "procurement.requisitions.create":  ["PM", "MNT"],
    "procurement.purchase_orders.read": ["PM", "MNT"],
    "procurement.purchase_orders.create": ["INV"],
    "maintenance.work_orders.read":     ["MNT"],
    "maintenance.work_orders.open":     ["INV"],
    "maintenance.material_demand.create": ["MNT"],
    "maintenance.assets.read":          ["MNT"],
}

_MODULE_LABELS: dict[str, str] = {
    "platform":              "Platform",
    "project_management":    "PM",
    "inventory_procurement": "INV",
    "maintenance_management": "MNT",
    "qhse":                  "QHSE",
    "hr_management":         "HR",
}

# Maps (source_module, target_module, capability) → bool (static rules).
# Dynamic check also requires both modules to be enabled at runtime.
_INTEGRATION_RULES: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("project_management", "inventory_procurement", "material_demand"),
        ("project_management", "inventory_procurement", "source_reference"),
        ("inventory_procurement", "project_management", "source_reference"),
        ("inventory_procurement", "maintenance_management", "source_reference"),
        ("maintenance_management", "inventory_procurement", "material_demand"),
        ("maintenance_management", "inventory_procurement", "source_reference"),
    }
)


class ModuleRegistry:
    """Central entitlement + capability gateway.

    Inject this into API classes and controllers.  Never import optional module
    code at the call site — use this registry to guard every cross-module action.
    """

    def __init__(self, module_runtime_service: ModuleRuntimeService) -> None:
        self._runtime = module_runtime_service

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
            "isMaintenanceEnabled": self.is_module_enabled("maintenance_management"),
            "isQhseEnabled": self.is_module_enabled("qhse"),
            "isHrManagementEnabled": self.is_module_enabled("hr_management"),
            # Cross-module integration pairs
            "canPmLinkInventory": self.can_use_integration(
                "project_management", "inventory_procurement", "material_demand"
            ),
            "canInventoryLinkPm": self.can_use_integration(
                "inventory_procurement", "project_management", "source_reference"
            ),
            "canInventoryLinkMaintenance": self.can_use_integration(
                "inventory_procurement", "maintenance_management", "source_reference"
            ),
            "canMaintenanceLinkInventory": self.can_use_integration(
                "maintenance_management", "inventory_procurement", "material_demand"
            ),
        }


__all__ = ["ModuleRegistry"]
