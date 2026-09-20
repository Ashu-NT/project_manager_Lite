from __future__ import annotations


class FinancialsCostMutationMixin:
    def _create_manual_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.create_manual_actual(
                dict(payload)
            ),
            "Manual actual draft created.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
        )

    def _update_actual_draft(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.update_actual_draft(
                dict(payload)
            ),
            "Manual actual draft updated.",
            on_success=lambda: self._invalidate_destinations("costs"),
        )

    def _delete_actual_draft(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.delete_actual_draft(
                dict(payload)
            ),
            "Manual actual draft deleted.",
            on_success=lambda: self._invalidate_destinations("costs"),
        )

    def _submit_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.submit_actual(
                dict(payload)
            ),
            "Actual submitted for approval.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
        )

    def _approve_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.approve_actual(
                dict(payload)
            ),
            "Actual approval decision recorded.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
        )

    def _reject_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.reject_actual(
                dict(payload)
            ),
            "Actual returned to draft.",
            on_success=lambda: self._invalidate_destinations("costs", "controls"),
        )

    def _post_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.post_actual(
                dict(payload)
            ),
            "Actual posted to the ledger.",
            on_success=lambda: self._invalidate_destinations(
                "overview", "costs", "performance", "controls"
            ),
        )

    def _reverse_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.reverse_actual(
                dict(payload)
            ),
            "Reversal posted.",
            on_success=lambda: self._invalidate_destinations(
                "overview", "costs", "performance", "controls"
            ),
        )
