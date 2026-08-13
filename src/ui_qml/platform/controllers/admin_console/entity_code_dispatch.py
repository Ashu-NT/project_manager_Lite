"""Cross-entity code-generation dispatch for the temporary Admin Console facade.

Why it still exists: `PlatformAdminWorkspaceController` exposes exactly one
`generateEntityCode(entity_type, payload)` QML slot that dispatches by string
across 7 entity types' own controllers. It exists only because AdminConsolePage.qml
calls one slot on one composite object instead of each entity page calling its own
controller's `generateCode()` directly.

What contract it preserves: byte-for-byte the same dispatch table and behavior
that previously lived in `controllers.admin.admin_entity_actions.generate_entity_code`.

Which later phase removes it: R2, when each capability's own page calls its own
controller's `generateCode()` directly and no single dispatcher is needed.
"""

from __future__ import annotations


def generate_entity_code(controller, entity_type: str, payload: dict) -> str:
    key = (entity_type or "").strip().lower()
    generators = {
        "organization": controller._organization_controller.generateCode,
        "site": controller._site_controller.generateCode,
        "department": controller._department_controller.generateCode,
        "employee": controller._employee_controller.generateCode,
        "party": controller._party_controller.generateCode,
        "document": controller._document_controller.generateCode,
        "document_structure": controller._document_structure_controller.generateCode,
    }
    handler = generators.get(key)
    if handler is None:
        return ""
    return handler(dict(payload))


__all__ = ["generate_entity_code"]
