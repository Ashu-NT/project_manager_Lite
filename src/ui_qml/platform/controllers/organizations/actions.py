from __future__ import annotations

from src.ui_qml.platform.controllers.common import run_admin_action

from .refresh import refresh_after_organization_change


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


def activate_organization(controller, organization_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.activateOrganization(
            organization_id
        ),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def deactivate_organization(controller, organization_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.deactivateOrganization(
            organization_id
        ),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def archive_organization(controller, organization_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.archiveOrganization(
            organization_id
        ),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def bulk_activate_organizations(controller) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.bulkActivateOrganizations(),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def bulk_deactivate_organizations(controller) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.bulkDeactivateOrganizations(),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def bulk_archive_organizations(controller) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.bulkArchiveOrganizations(),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def apply_bulk_organization_currency(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.applyBulkOrganizationCurrency(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def apply_bulk_organization_timezone(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.applyBulkOrganizationTimezone(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


def apply_bulk_organization_modules(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._organization_controller.applyBulkOrganizationModules(payload),
        on_success=lambda: refresh_after_organization_change(controller),
    )


__all__ = [
    "activate_organization",
    "apply_bulk_organization_currency",
    "apply_bulk_organization_modules",
    "apply_bulk_organization_timezone",
    "archive_organization",
    "bulk_activate_organizations",
    "bulk_archive_organizations",
    "bulk_deactivate_organizations",
    "create_organization",
    "deactivate_organization",
    "update_organization",
]
