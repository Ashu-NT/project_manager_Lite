"""IntegrationResolver — resolves cross-module references for UI and API.

Given a CrossModuleReference (soft link with snapshots), returns a
ResolvedReference that is always safe to display even when the target module
is disabled or the source record is missing.

Route templates map (module_id, entity_type) → route_id used by the shell
router.  route_id is a workspace address; entity-level deep-linking is handled
by each workspace's controller using the entity_id from the resolved reference.
"""

from __future__ import annotations

from src.core.platform.integration.cross_module_reference import (
    CrossModuleReference,
    ResolvedReference,
)
from src.core.platform.integration.module_registry import ModuleRegistry

# Maps (module_id, entity_type) → shell route_id for the workspace that owns it.
_ROUTE_TEMPLATES: dict[tuple[str, str], str] = {
    ("project_management", "project"): "project_management.projects",
    ("project_management", "task"): "project_management.tasks",
    ("project_management", "resource"): "project_management.resources",
    ("project_management", "portfolio"): "project_management.portfolio",
    ("inventory_procurement", "stock_item"): "inventory_procurement.catalog",
    ("inventory_procurement", "reservation"): "inventory_procurement.reservations",
    ("inventory_procurement", "requisition"): "inventory_procurement.procurement",
    ("inventory_procurement", "purchase_order"): "inventory_procurement.procurement",
    ("inventory_procurement", "storeroom"): "inventory_procurement.inventory",
    ("maintenance_management", "asset"): "maintenance.assets",
    ("maintenance_management", "work_order"): "maintenance.work_orders",
    ("maintenance_management", "work_request"): "maintenance.work_requests",
    ("maintenance_management", "preventive_plan"): "maintenance.preventive",
}


class IntegrationResolver:
    """Resolves CrossModuleReference into display-safe ResolvedReference."""

    def __init__(self, module_registry: ModuleRegistry) -> None:
        self._registry = module_registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_route(
        self,
        module_id: str,
        entity_type: str,
        entity_id: str,  # noqa: ARG002 — reserved for future deep-link support
    ) -> str | None:
        return _ROUTE_TEMPLATES.get((module_id, entity_type))

    def resolve_reference(self, ref: CrossModuleReference) -> ResolvedReference:
        module_enabled = self._registry.is_module_enabled(ref.module_id)
        route = self.build_route(ref.module_id, ref.entity_type, ref.entity_id)
        route_available = route is not None
        can_open = module_enabled and route_available

        if not module_enabled:
            disabled_reason = "Module not enabled"
        elif not route_available:
            disabled_reason = "Navigation not available"
        else:
            disabled_reason = ""

        display_title = ref.title_snapshot or ref.code_snapshot or f"{ref.entity_type} {ref.entity_id}"
        display_subtitle = ref.code_snapshot if ref.title_snapshot else ""
        display_status = ref.status_snapshot

        return ResolvedReference(
            module_id=ref.module_id,
            entity_type=ref.entity_type,
            entity_id=ref.entity_id,
            code_snapshot=ref.code_snapshot,
            title_snapshot=ref.title_snapshot,
            status_snapshot=ref.status_snapshot,
            module_enabled=module_enabled,
            source_available=True,
            route_available=route_available,
            can_open=can_open,
            disabled_reason=disabled_reason,
            route=route,
            display_title=display_title,
            display_subtitle=display_subtitle,
            display_status=display_status,
        )

    def display_reference(self, ref: CrossModuleReference) -> dict[str, object]:
        return self.resolve_reference(ref).as_dict()

    def resolve_missing_source(
        self,
        module_id: str,
        entity_type: str,
        entity_id: str,
        code_snapshot: str = "",
        title_snapshot: str = "",
        status_snapshot: str = "",
    ) -> ResolvedReference:
        """Return a ResolvedReference representing a deleted/unavailable source record."""
        display_title = title_snapshot or code_snapshot or f"{entity_type} {entity_id}"
        return ResolvedReference(
            module_id=module_id,
            entity_type=entity_type,
            entity_id=entity_id,
            code_snapshot=code_snapshot,
            title_snapshot=title_snapshot,
            status_snapshot=status_snapshot,
            module_enabled=self._registry.is_module_enabled(module_id),
            source_available=False,
            route_available=False,
            can_open=False,
            disabled_reason="Source unavailable",
            route=None,
            display_title=display_title,
            display_subtitle=code_snapshot if title_snapshot else "",
            display_status=status_snapshot,
        )

    # ------------------------------------------------------------------
    # Helper — build CrossModuleReference from ORM soft-reference fields
    # ------------------------------------------------------------------

    @staticmethod
    def from_soft_reference(
        source_module: str | None,
        source_entity_type: str | None,
        source_entity_id: str | None,
        source_code_snapshot: str | None = None,
        source_title_snapshot: str | None = None,
        source_status_snapshot: str | None = None,
    ) -> CrossModuleReference | None:
        """Build a CrossModuleReference from ORM soft-reference columns.

        Returns None if any of the three identity fields are blank —
        that means no cross-module link is set.
        """
        if not (source_module and source_entity_type and source_entity_id):
            return None
        return CrossModuleReference(
            module_id=source_module,
            entity_type=source_entity_type,
            entity_id=source_entity_id,
            code_snapshot=source_code_snapshot or "",
            title_snapshot=source_title_snapshot or "",
            status_snapshot=source_status_snapshot or "",
        )


__all__ = ["IntegrationResolver"]
