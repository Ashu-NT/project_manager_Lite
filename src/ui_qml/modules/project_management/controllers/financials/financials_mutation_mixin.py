from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
)
from src.ui_qml.modules.project_management.utils.file_paths import (
    local_path_from_qml_file_url,
)


class FinancialsMutationMixin:
    def _run_budget_mutation(self, operation, success_message: str) -> dict[str, object]:
        result = run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=lambda: self._invalidate_destinations(
                "overview", "planning", "performance"
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )
        if result.get("conflict"):
            # Keep dialog input intact while replacing stale read evidence.
            self._invalidate_destinations("planning")
        return result

    def _create_budget_version(
        self, project_id: str, name: str, currency: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.create_budget_version(
                project_id, name, currency
            ),
            "Budget version created.",
        )

    def _create_budget_successor(
        self, predecessor_id: str, name: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.create_budget_successor(
                predecessor_id, name
            ),
            "Draft successor created from the approved Budget.",
        )

    def _update_budget(
        self, budget_id: str, version: int, name: str, notes: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.update_budget(
                budget_id, version, name, notes
            ),
            "Budget details updated.",
        )

    def _delete_budget(self, budget_id: str, version: int) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.delete_budget(
                budget_id, version
            ),
            "Draft Budget deleted.",
        )

    def _add_budget_line(self, *args) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.add_budget_line(*args),
            "Budget line added.",
        )

    def _update_budget_line(self, *args) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.update_budget_line(*args),
            "Budget line updated.",
        )

    def _delete_budget_line(
        self, line_id: str, line_version: int, parent_version: int
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.delete_budget_line(
                line_id, line_version, parent_version
            ),
            "Budget line deleted.",
        )

    def _submit_budget(
        self, budget_id: str, version: int, notes: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.submit_budget(
                budget_id, version, notes
            ),
            "Budget submitted and frozen for review.",
        )

    def _request_budget_approval(
        self, budget_id: str, version: int, notes: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.request_budget_approval(
                budget_id, version, notes
            ),
            "Budget approval request created.",
        )

    def _decide_budget_approval(
        self, request_id: str, approve: bool, notes: str
    ) -> dict[str, object]:
        action = "approved" if approve else "rejected"
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.decide_budget_approval(
                request_id, approve, notes
            ),
            f"Budget approval request {action}.",
        )

    def _close_budget(
        self, budget_id: str, version: int, notes: str
    ) -> dict[str, object]:
        return self._run_budget_mutation(
            lambda: self._financials_workspace_presenter.close_budget(
                budget_id, version, notes
            ),
            "Approved Budget closed.",
        )

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
