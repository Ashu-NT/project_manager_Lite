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

    def _bulk_delete_costs(self, cost_ids: list) -> dict[str, object]:
        ids = [str(item_id) for item_id in (cost_ids or [])]
        if not ids:
            return {"ok": False, "message": "No cost items selected."}
        return run_mutation(
            operation=lambda: [
                self._financials_workspace_presenter.delete_cost_item(item_id)
                for item_id in ids
            ],
            success_message=f"{len(ids)} cost item(s) deleted.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _apply_bulk_cost_type(self, payload: dict[str, object]) -> dict[str, object]:
        ids = list(self._selected_cost_ids)
        cost_type = str(payload.get("value") or payload.get("costType") or "")
        if not ids or not cost_type:
            return {"ok": False, "message": "No items or cost type selected."}
        return run_mutation(
            operation=lambda: [
                self._financials_workspace_presenter.update_cost_item(
                    {"id": item_id, "costType": cost_type}
                )
                for item_id in ids
            ],
            success_message=f"Cost type updated for {len(ids)} item(s).",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _generate_entity_code(self, entity_type: str, payload: dict[str, object]) -> str:
        if (entity_type or "").strip().lower() != "cost":
            return ""
        try:
            return self._financials_workspace_presenter.suggest_code(dict(payload))
        except Exception as exc:  # noqa: BLE001 - surface to dialog/banner
            self._set_error_message(str(exc))
            return ""

    def _create_cost_item(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.create_cost_item(
                dict(payload)
            ),
            success_message="Cost item created.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _update_cost_item(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.update_cost_item(
                dict(payload)
            ),
            success_message="Cost item updated.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _delete_cost_item(self, cost_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.delete_cost_item(
                cost_id
            ),
            success_message="Cost item deleted.",
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )


__all__ = ["FinancialsMutationMixin"]
