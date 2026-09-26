from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
)


class FinancialsMutationMixin:
    def _run_finance_mutation(
        self, operation, success_message: str, on_success
    ) -> dict[str, object]:
        if self._is_busy:
            return {
                "ok": False,
                "message": "A financial command is already in progress.",
                "code": "FINANCE_COMMAND_BUSY",
                "category": "busy",
            }
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=on_success,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
            safe_validation_message="Review the highlighted financial fields and try again.",
            safe_validation_code="FINANCE_INPUT_INVALID",
            safe_failure_message=(
                "The financial change could not be completed. Try again or refresh "
                "the workspace."
            ),
            safe_failure_code="FINANCE_MUTATION_FAILED",
        )
