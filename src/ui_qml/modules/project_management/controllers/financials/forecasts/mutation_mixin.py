from __future__ import annotations


class FinancialsForecastsMutationMixin:
    def _run_forecast_mutation(self, operation, success_message: str) -> dict[str, object]:
        result = self._run_finance_mutation(
            operation,
            success_message,
            on_success=lambda: self._invalidate_destinations(
                "overview", "planning", "performance"
            ),
        )
        if result.get("conflict"):
            self._invalidate_destinations("planning")
        return result

    def _generate_forecast(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_forecast_mutation(
            lambda: self._financials_workspace_presenter.generate_forecast(dict(payload)),
            "Forecast draft generated from authoritative financial sources.",
        )

    def _submit_forecast(
        self, forecast_id: str, version: int, notes: str
    ) -> dict[str, object]:
        return self._run_forecast_mutation(
            lambda: self._financials_workspace_presenter.submit_forecast(
                forecast_id, version, notes
            ),
            "Forecast submitted and frozen for review.",
        )

    def _request_forecast_approval(
        self, forecast_id: str, version: int, notes: str
    ) -> dict[str, object]:
        return self._run_forecast_mutation(
            lambda: self._financials_workspace_presenter.request_forecast_approval(
                forecast_id, version, notes
            ),
            "Forecast approval request created.",
        )

    def _decide_forecast_approval(
        self, request_id: str, approve: bool, notes: str
    ) -> dict[str, object]:
        action = "approved" if approve else "rejected"
        return self._run_forecast_mutation(
            lambda: self._financials_workspace_presenter.decide_forecast_approval(
                request_id, approve, notes
            ),
            f"Forecast approval request {action}.",
        )
