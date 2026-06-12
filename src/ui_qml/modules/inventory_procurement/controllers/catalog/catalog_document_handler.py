from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def link_document(ctrl, item_id: str, document_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.link_document(
            item_id, document_id
        ),
        success_message="Document linked.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )


def unlink_document(ctrl, item_id: str, document_id: str) -> dict[str, object]:
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.unlink_document(
            item_id, document_id
        ),
        success_message="Document unlinked.",
        on_success=ctrl.refresh,
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
