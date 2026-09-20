from __future__ import annotations


class FinancialsInvoicingMutationMixin:
    def _run_billing_mutation(self, operation, success_message: str) -> dict[str, object]:
        result = self._run_finance_mutation(
            operation,
            success_message,
            on_success=lambda: self._invalidate_destinations("commercial"),
        )
        if result.get("conflict"):
            self._invalidate_destinations("commercial")
        return result

    def _create_billing_profile(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.create_billing_profile(dict(payload)),
            "Billing profile created.",
        )

    def _activate_billing_profile(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.activate_billing_profile(dict(payload)),
            "Billing profile activated.",
        )

    def _add_billing_schedule_line(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.add_billing_schedule_line(dict(payload)),
            "Billing schedule line added.",
        )

    def _mark_billing_schedule_line_ready(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.mark_billing_schedule_line_ready(dict(payload)),
            "Billing schedule line marked ready.",
        )

    def _create_billing_preparation(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.create_billing_preparation(dict(payload)),
            "Billing preparation created.",
        )

    def _add_billing_source(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.add_billing_source(dict(payload)),
            "Billing source added.",
        )

    def _remove_billing_line(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.remove_billing_line(dict(payload)),
            "Draft billing line removed.",
        )

    def _cancel_billing_preparation(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.cancel_billing_preparation(dict(payload)),
            "Draft billing preparation cancelled.",
        )

    def _submit_billing_preparation(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.submit_billing_preparation(dict(payload)),
            "Billing preparation submitted for approval.",
        )

    def _request_billing_delivery(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.request_billing_delivery(dict(payload)),
            "Billing preparation queued for Accounting delivery.",
        )

    def _decide_billing_approval(self, request_id: str, approve: bool, note: str = "") -> dict[str, object]:
        action = "approved" if approve else "rejected"
        return self._run_billing_mutation(
            lambda: self._financials_workspace_presenter.decide_billing_approval(
                request_id, approve, note
            ),
            f"Billing preparation {action}.",
        )
