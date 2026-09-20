from __future__ import annotations


class FinancialsFinancialChangesMutationMixin:
    def _run_financial_change_mutation(
        self, operation, success_message: str
    ) -> dict[str, object]:
        result = self._run_finance_mutation(
            operation,
            success_message,
            on_success=lambda: self._invalidate_destinations("controls"),
        )
        if result.get("conflict"):
            self._invalidate_destinations("controls")
        return result

    def _create_financial_change(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.create_financial_change(
                dict(payload)
            ),
            "Change Request created.",
        )

    def _update_financial_change(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.update_financial_change(
                dict(payload)
            ),
            "Change Request updated.",
        )

    def _add_financial_change_impact(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.add_financial_change_impact(
                dict(payload)
            ),
            "Financial Change impact added.",
        )

    def _update_financial_change_impact(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.update_financial_change_impact(
                dict(payload)
            ),
            "Financial Change impact updated.",
        )

    def _remove_financial_change_impact(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.remove_financial_change_impact(
                dict(payload)
            ),
            "Financial Change impact removed.",
        )

    def _submit_financial_change(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_financial_change_mutation(
            lambda: self._financials_workspace_presenter.submit_financial_change(
                dict(payload)
            ),
            "Change Request submitted for approval.",
        )

    def _decide_financial_change(
        self, request_id: str, approve: bool, notes: str
    ) -> dict[str, object]:
        action = "approved and applied" if approve else "rejected"
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.decide_financial_change_approval(
                request_id, approve, notes
            ),
            f"Financial Change {action}.",
            on_success=lambda: self._invalidate_destinations(
                "controls", "planning", "overview", "performance", "commercial"
            ),
        )
