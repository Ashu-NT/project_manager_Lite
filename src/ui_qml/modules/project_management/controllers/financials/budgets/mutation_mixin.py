from __future__ import annotations


class FinancialsBudgetsMutationMixin:
    def _run_budget_mutation(self, operation, success_message: str) -> dict[str, object]:
        result = self._run_finance_mutation(
            operation,
            success_message,
            on_success=lambda: self._invalidate_destinations(
                "overview", "planning", "performance"
            ),
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
