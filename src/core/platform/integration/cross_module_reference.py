"""Cross-module reference value objects.

CrossModuleReference stores a soft link to an entity in another module.
ResolvedReference is the display-safe result after checking module availability.

Use soft references (module_id / entity_type / entity_id + snapshots) for optional
module links so that disabled modules never crash the app — snapshot text stays
readable even when the target module is off.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrossModuleReference:
    """Immutable value object describing an optional cross-module link."""

    module_id: str
    entity_type: str
    entity_id: str

    code_snapshot: str = ""
    title_snapshot: str = ""
    status_snapshot: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "moduleId": self.module_id,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "codeSnapshot": self.code_snapshot,
            "titleSnapshot": self.title_snapshot,
            "statusSnapshot": self.status_snapshot,
        }


@dataclass(frozen=True)
class ResolvedReference:
    """Display-safe result of resolving a CrossModuleReference."""

    module_id: str
    entity_type: str
    entity_id: str

    code_snapshot: str
    title_snapshot: str
    status_snapshot: str

    module_enabled: bool
    source_available: bool
    route_available: bool

    can_open: bool
    disabled_reason: str
    route: str | None

    display_title: str
    display_subtitle: str
    display_status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "moduleId": self.module_id,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "codeSnapshot": self.code_snapshot,
            "titleSnapshot": self.title_snapshot,
            "statusSnapshot": self.status_snapshot,
            "moduleEnabled": self.module_enabled,
            "sourceAvailable": self.source_available,
            "routeAvailable": self.route_available,
            "canOpen": self.can_open,
            "disabledReason": self.disabled_reason,
            "route": self.route,
            "displayTitle": self.display_title,
            "displaySubtitle": self.display_subtitle,
            "displayStatus": self.display_status,
        }


__all__ = ["CrossModuleReference", "ResolvedReference"]
