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


def refresh_after_organization_change(controller) -> None:
    refresh_overview(controller)
    controller._calendar_controller.refresh()
    controller._site_controller.refresh()
    controller._department_controller.refresh()
    controller._employee_controller.refresh()
    controller._party_controller.refresh()
    controller._document_controller.refresh()
    controller._document_structure_controller.refresh()
    refresh_empty_state(controller)


def refresh_after_site_change(controller) -> None:
    refresh_overview(controller)
    controller._department_controller.refresh()
    controller._employee_controller.refresh()
    refresh_empty_state(controller)


def refresh_after_calendar_change(controller) -> None:
    controller._calendar_controller.refresh()
    refresh_empty_state(controller)


def refresh_after_department_change(controller) -> None:
    refresh_overview(controller)
    controller._employee_controller.refresh()
    refresh_empty_state(controller)


def refresh_after_employee_change(controller) -> None:
    refresh_overview(controller)
    refresh_empty_state(controller)


def refresh_after_user_change(controller) -> None:
    refresh_overview(controller)
    refresh_empty_state(controller)


def refresh_after_party_change(controller) -> None:
    refresh_overview(controller)
    refresh_empty_state(controller)


def refresh_after_document_change(controller) -> None:
    refresh_overview(controller)
    refresh_empty_state(controller)


def refresh_after_document_structure_change(controller) -> None:
    controller._document_controller.refresh()
    refresh_empty_state(controller)


def refresh_after_document_link_change(controller) -> None:
    refresh_empty_state(controller)


__all__ = [
    "do_refresh",
    "refresh_after_calendar_change",
    "refresh_after_department_change",
    "refresh_after_document_change",
    "refresh_after_document_link_change",
    "refresh_after_document_structure_change",
    "refresh_after_employee_change",
    "refresh_after_organization_change",
    "refresh_after_party_change",
    "refresh_after_site_change",
    "refresh_after_user_change",
    "refresh_empty_state",
    "refresh_overview",
]
