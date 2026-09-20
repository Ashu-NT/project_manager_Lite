from __future__ import annotations


class FinancialsRateCardsMutationMixin:
    def _run_rate_mutation(self, operation, success_message: str) -> dict[str, object]:
        result = self._run_finance_mutation(
            operation,
            success_message,
            on_success=lambda: self._invalidate_destinations("costs"),
        )
        if result.get("conflict"):
            self._invalidate_destinations("costs")
        return result

    def _create_rate_card(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.create_rate_card(dict(payload)),
            "Rate Card created.",
        )

    def _update_rate_card(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.update_rate_card(dict(payload)),
            "Rate Card updated.",
        )

    def _deactivate_rate_card(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.deactivate_rate_card(dict(payload)),
            "Rate Card deactivated.",
        )

    def _add_rate_line(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.add_rate_line(dict(payload)),
            "Rate Line added.",
        )

    def _update_rate_line(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.update_rate_line(dict(payload)),
            "Rate Line updated.",
        )

    def _deactivate_rate_line(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_rate_mutation(
            lambda: self._financials_workspace_presenter.deactivate_rate_line(dict(payload)),
            "Rate Line deactivated.",
        )
