
from __future__ import annotations

from src.ui_qml.platform.controllers.common import WORKSPACE_PERMISSIONS, serialize_workspace_overview

# entity -> (required permission codes, controller attribute name)
_ENTITY_CONTROLLERS: dict[str, tuple[tuple[str, ...], str]] = {
    "organization": (WORKSPACE_PERMISSIONS["organization"], "_organization_controller"),
    "calendar": (WORKSPACE_PERMISSIONS["calendar"], "_calendar_controller"),
    "site": (WORKSPACE_PERMISSIONS["site"], "_site_controller"),
    "department": (WORKSPACE_PERMISSIONS["department"], "_department_controller"),
    "employee": (WORKSPACE_PERMISSIONS["employee"], "_employee_controller"),
    "user": (WORKSPACE_PERMISSIONS["user"], "_user_controller"),
    "party": (WORKSPACE_PERMISSIONS["party"], "_party_controller"),
    "document": (WORKSPACE_PERMISSIONS["document"], "_document_controller"),
    "document_structure": (WORKSPACE_PERMISSIONS["document_structure"], "_document_structure_controller"),
}


def _current_permissions(controller) -> frozenset[str] | None:
    """None means "unknown, fail open" -- no runtime API wired (QML
    preview, or a test constructing this controller directly without
    one), or a transient error fetching permissions. This is a perf
    pre-filter, not the actual authorization boundary, so an unknown
    state should refresh everything rather than go blank."""
    runtime_api = getattr(controller, "_runtime_api", None)
    if runtime_api is None:
        return None
    result = runtime_api.get_current_permissions()
    if not getattr(result, "ok", False) or getattr(result, "data", None) is None:
        return None
    return frozenset(result.data)


def do_refresh(controller) -> None:
    controller._set_is_loading(True)
    controller._set_error_message("")
    refresh_overview(controller)
    permissions = _current_permissions(controller)
    for required_codes, attr_name in _ENTITY_CONTROLLERS.values():
        if permissions is None or any(code in permissions for code in required_codes):
            getattr(controller, attr_name).refresh()
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
