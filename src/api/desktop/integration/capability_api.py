"""IntegrationCapabilityDesktopApi — desktop-facing integration layer.

Exposes module capability checks and cross-module reference resolution to
controllers and presenters without them needing to import optional module code.

Usage in a controller:
    enabled = self._integration_api.is_module_enabled("inventory_procurement")
    resolved = self._integration_api.resolve_soft_reference(
        source_module=orm.source_module,
        source_entity_type=orm.source_entity_type,
        source_entity_id=orm.source_reference_id,
        source_code_snapshot=orm.source_code_snapshot,
        source_title_snapshot=orm.source_title_snapshot,
        source_status_snapshot=orm.source_status_snapshot,
    )
    # resolved is a plain dict — safe to return to QML
"""

from __future__ import annotations

from dataclasses import dataclass
from src.core.platform.integration.cross_module_reference import CrossModuleReference
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver


@dataclass(frozen=True)
class IntegrationCapabilityDesktopApi:
    module_registry: ModuleRegistry
    resolver: IntegrationResolver

    # ------------------------------------------------------------------
    # Module / capability checks
    # ------------------------------------------------------------------

    def is_module_enabled(self, module_id: str) -> bool:
        return self.module_registry.is_module_enabled(module_id)

    def has_capability(self, capability_id: str) -> bool:
        return self.module_registry.has_capability(capability_id)

    def can_use_integration(
        self,
        source_module: str,
        target_module: str,
        capability: str,
    ) -> bool:
        return self.module_registry.can_use_integration(source_module, target_module, capability)

    def capability_snapshot(self) -> dict[str, bool]:
        return self.module_registry.capability_snapshot()

    def list_integration_capabilities(self) -> list[dict]:
        return self.module_registry.list_capabilities()

    # ------------------------------------------------------------------
    # Reference resolution
    # ------------------------------------------------------------------

    def resolve_reference(self, ref: CrossModuleReference) -> dict:
        return self.resolver.display_reference(ref)

    def resolve_soft_reference(
        self,
        source_module: str | None,
        source_entity_type: str | None,
        source_entity_id: str | None,
        source_code_snapshot: str | None = None,
        source_title_snapshot: str | None = None,
        source_status_snapshot: str | None = None,
    ) -> dict:
        """Resolve ORM soft-reference columns into a display-safe dict.

        Returns a safe empty dict if no source link is set.
        """
        ref = IntegrationResolver.from_soft_reference(
            source_module,
            source_entity_type,
            source_entity_id,
            source_code_snapshot,
            source_title_snapshot,
            source_status_snapshot,
        )
        if ref is None:
            return {
                "moduleId": None,
                "entityType": None,
                "entityId": None,
                "codeSnapshot": "",
                "titleSnapshot": "",
                "statusSnapshot": "",
                "moduleEnabled": False,
                "sourceAvailable": False,
                "routeAvailable": False,
                "canOpen": False,
                "disabledReason": "",
                "route": None,
                "displayTitle": "",
                "displaySubtitle": "",
                "displayStatus": "",
            }
        return self.resolver.display_reference(ref)


def build_integration_capability_api(
    module_registry: ModuleRegistry,
) -> IntegrationCapabilityDesktopApi:
    resolver = IntegrationResolver(module_registry)
    return IntegrationCapabilityDesktopApi(
        module_registry=module_registry,
        resolver=resolver,
    )


__all__ = ["IntegrationCapabilityDesktopApi", "build_integration_capability_api"]
