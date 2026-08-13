"""Cross-capability refresh aggregation for the temporary Admin Console facade.

Why it still exists: `do_refresh`/`refresh_overview`/`refresh_empty_state` have no
single-entity owner by construction -- they aggregate state across all 9 entities
`PlatformAdminWorkspaceController` composes. Capability-specific refresh cascades
(triggered by a specific entity's mutation) live in that capability's own
`refresh.py` instead (see e.g. `controllers.organization.employees.refresh`),
which call back into `refresh_overview`/`refresh_empty_state` here for their
cross-cutting consequences.

What contract it preserves: byte-for-byte the same three functions and bodies
that previously lived in `controllers.admin.admin_refresh_service`.

Which later phase removes it: R2 (approved R0 design doc, Implementation Phases
table), when AdminConsolePage.qml's composition is replaced by the unified
Platform workspace and no single controller composes all 9 entities anymore.
"""

from __future__ import annotations

from src.ui_qml.platform.controllers.common import serialize_workspace_overview


def do_refresh(controller) -> None:
    controller._set_is_loading(True)
    controller._set_error_message("")
    refresh_overview(controller)
    controller._organization_controller.refresh()
    controller._calendar_controller.refresh()
    controller._site_controller.refresh()
    controller._department_controller.refresh()
    controller._employee_controller.refresh()
    controller._user_controller.refresh()
    controller._party_controller.refresh()
    controller._document_controller.refresh()
    controller._document_structure_controller.refresh()
    refresh_empty_state(controller)
    controller._set_is_loading(False)


def refresh_overview(controller) -> None:
    controller._set_overview(
        serialize_workspace_overview(controller._overview_presenter.build_overview())
    )


def refresh_empty_state(controller) -> None:
    has_items = any(
        catalog.get("items")
        for catalog in (
            controller.organizations,
            controller.calendars,
            controller.sites,
            controller.departments,
            controller.employees,
            controller.users,
            controller.parties,
            controller.documents,
        )
    )
    controller._set_empty_state(
        "" if has_items else "No platform administration records are available yet."
    )


__all__ = ["do_refresh", "refresh_empty_state", "refresh_overview"]
