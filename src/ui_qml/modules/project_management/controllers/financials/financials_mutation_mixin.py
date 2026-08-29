from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
)
from src.ui_qml.modules.project_management.utils.file_paths import (
    local_path_from_qml_file_url,
)


class FinancialsMutationMixin:
    def _export_financials(self, report_format: str, output_path: str) -> None:
        normalized_path = local_path_from_qml_file_url(output_path)
        if not normalized_path:
            self._set_error_message("Choose an output file for the financial report.")
            return
        run_mutation(
            operation=lambda: self._financials_workspace_presenter.export_financial_report(
                project_id=self._selected_project_id,
                output_path=normalized_path,
                report_format=(report_format or "").strip().lower(),
                baseline_id=self._selected_baseline_id or None,
            ),
            success_message=f"Financial report exported to {normalized_path}.",
            on_success=lambda: None,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _create_manual_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.create_manual_actual(
                dict(payload)
            ),
            success_message="Manual actual draft created.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _create_cost_code(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.create_cost_code(
                dict(payload)
            ),
            success_message="Cost code created and made available to the project.",
            on_success=lambda: self._invalidate_destinations(
                "planning", "costs", "controls"
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _submit_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.submit_actual(
                dict(payload)
            ),
            success_message="Actual submitted for approval.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _approve_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.approve_actual(
                dict(payload)
            ),
            success_message="Actual approval decision recorded.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _reject_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.reject_actual(
                dict(payload)
            ),
            success_message="Actual returned to draft.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _post_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.post_actual(
                dict(payload)
            ),
            success_message="Actual posted to the ledger.",
            on_success=lambda: self._invalidate_destinations(
                "overview", "costs", "performance", "controls"
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _reverse_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.reverse_actual(
                dict(payload)
            ),
            success_message="Reversal posted.",
            on_success=lambda: self._invalidate_destinations(
                "overview", "costs", "performance", "controls"
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

__all__ = ["FinancialsMutationMixin"]
