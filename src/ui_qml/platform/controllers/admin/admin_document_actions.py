from __future__ import annotations

from .admin_action_runner import run_admin_action
from .admin_refresh_service import (
    refresh_after_document_change,
    refresh_after_document_link_change,
    refresh_after_document_structure_change,
)


def create_document(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_controller.createDocument(payload),
        on_success=lambda: refresh_after_document_change(controller),
    )


def update_document(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_controller.updateDocument(payload),
        on_success=lambda: refresh_after_document_change(controller),
    )


def toggle_document_active(controller, document_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_controller.toggleDocumentActive(document_id),
        on_success=lambda: refresh_after_document_change(controller),
    )


def select_document(controller, document_id: str) -> None:
    controller._document_controller.selectDocument(document_id)


def create_document_structure(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_structure_controller.createDocumentStructure(
            payload
        ),
        on_success=lambda: refresh_after_document_structure_change(controller),
    )


def update_document_structure(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_structure_controller.updateDocumentStructure(
            payload
        ),
        on_success=lambda: refresh_after_document_structure_change(controller),
    )


def toggle_document_structure_active(controller, structure_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_structure_controller.toggleDocumentStructureActive(
            structure_id
        ),
        on_success=lambda: refresh_after_document_structure_change(controller),
    )


def add_document_link(controller, payload: dict) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_controller.addDocumentLink(payload),
        on_success=lambda: refresh_after_document_link_change(controller),
    )


def remove_document_link(controller, link_id: str) -> dict[str, object]:
    return run_admin_action(
        controller,
        action=lambda: controller._document_controller.removeDocumentLink(link_id),
        on_success=lambda: refresh_after_document_link_change(controller),
    )


__all__ = [
    "add_document_link",
    "create_document",
    "create_document_structure",
    "remove_document_link",
    "select_document",
    "toggle_document_active",
    "toggle_document_structure_active",
    "update_document",
    "update_document_structure",
]
