from __future__ import annotations


class FinancialsGovernanceMutationMixin:
    def _create_cost_code(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.create_cost_code(
                dict(payload)
            ),
            "Cost code created and made available to the project.",
            on_success=lambda: self._invalidate_destinations(
                "planning", "costs", "controls"
            ),
        )

    def _update_financial_profile(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.update_financial_profile(dict(payload)),
            "Financial setup updated.",
            on_success=lambda: self._invalidate_destinations("controls", "planning", "costs"),
        )

    def _transition_financial_profile(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.transition_financial_profile(dict(payload)),
            "Financial profile status updated.",
            on_success=lambda: self._invalidate_destinations("controls"),
        )

    def _update_cost_code(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.update_cost_code(dict(payload)),
            "Cost code updated.",
            on_success=lambda: self._invalidate_destinations("controls", "planning", "costs"),
        )

    def _change_cost_code_status(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.change_cost_code_status(dict(payload)),
            "Cost-code status updated.",
            on_success=lambda: self._invalidate_destinations("controls", "planning", "costs"),
        )

    def _add_cost_code_restriction(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.add_cost_code_restriction(dict(payload)),
            "Cost code added to the project allow-list.",
            on_success=lambda: self._invalidate_destinations("controls", "planning", "costs"),
        )

    def _remove_cost_code_restriction(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_finance_mutation(
            lambda: self._financials_workspace_presenter.remove_cost_code_restriction(dict(payload)),
            "Cost code removed from the project allow-list.",
            on_success=lambda: self._invalidate_destinations("controls", "planning", "costs"),
        )
