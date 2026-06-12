from __future__ import annotations

from .admin_action_runner import run_admin_action
from .admin_refresh_service import (
    refresh_after_department_change,
    refresh_after_employee_change,
    refresh_after_organization_change,
    refresh_after_party_change,
    refresh_after_site_change,
    refresh_after_user_change,
)


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


def create_organization(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.createOrganization(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def update_organization(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.updateOrganization(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def set_active_organization(controller, organization_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.setActiveOrganization(
            organization_id
        ),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def create_site(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.createSite(payload),
        on_success=lambda: refresh_after_site_change(controller),
    )


def update_site(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.updateSite(payload),
        on_success=lambda: refresh_after_site_change(controller),
    )


def toggle_site_active(controller, site_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._site_controller.toggleSiteActive(site_id),
        on_success=lambda: refresh_after_site_change(controller),
    )


def create_department(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.createDepartment(payload),
        on_success=lambda: refresh_after_department_change(controller),
    )


def update_department(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.updateDepartment(payload),
        on_success=lambda: refresh_after_department_change(controller),
    )


def toggle_department_active(controller, department_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._department_controller.toggleDepartmentActive(department_id),
        on_success=lambda: refresh_after_department_change(controller),
    )


def create_employee(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.createEmployee(payload),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def update_employee(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.updateEmployee(payload),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def toggle_employee_active(controller, employee_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._employee_controller.toggleEmployeeActive(employee_id),
        on_success=lambda: refresh_after_employee_change(controller),
    )


def create_user(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.createUser(payload),
        on_success=lambda: refresh_after_user_change(controller),
    )


def update_user(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.updateUser(payload),
        on_success=lambda: refresh_after_user_change(controller),
    )


def toggle_user_active(controller, user_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._user_controller.toggleUserActive(user_id),
        on_success=lambda: refresh_after_user_change(controller),
    )


def create_party(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.createParty(payload),
        on_success=lambda: refresh_after_party_change(controller),
    )


def update_party(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.updateParty(payload),
        on_success=lambda: refresh_after_party_change(controller),
    )


def toggle_party_active(controller, party_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._party_controller.togglePartyActive(party_id),
        on_success=lambda: refresh_after_party_change(controller),
    )


__all__ = [
    "create_department",
    "create_employee",
    "create_organization",
    "create_party",
    "create_site",
    "create_user",
    "generate_entity_code",
    "set_active_organization",
    "toggle_department_active",
    "toggle_employee_active",
    "toggle_party_active",
    "toggle_site_active",
    "toggle_user_active",
    "update_department",
    "update_employee",
    "update_organization",
    "update_party",
    "update_site",
    "update_user",
]
