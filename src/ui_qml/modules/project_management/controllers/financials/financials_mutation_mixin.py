from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_financials_forecast_view_model,
)


class FinancialsMutationMixin:
    def _compute_forecast(self, method: str) -> dict[str, object]:
        normalized = (method or "bac_over_cpi").strip().lower()
        return run_mutation(
            operation=lambda: self._apply_forecast(normalized),
            success_message="Forecast recalculated.",
            on_success=lambda: None,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _apply_forecast(self, method: str) -> None:
        vm = self._financials_workspace_presenter.compute_forecast(
            self._selected_project_id,
            method=method,
        )
        self._set_forecast(serialize_financials_forecast_view_model(vm))

    def _export_financials(self) -> None:
        self._set_error_message("")
        self._set_feedback_message(
            "Export is not available here. Open the Reports section to generate financial summaries, cost breakdowns, and variance exports."
        )

    def _create_manual_actual(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.create_manual_actual(
                dict(payload)
            ),
            success_message="Manual actual draft created.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

__all__ = ["FinancialsMutationMixin"]
