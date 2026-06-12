from __future__ import annotations

from typing import Callable

from src.ui_qml.modules.project_management.controllers.common import run_mutation

class TimesheetsMutationHandler:
    def __init__(
        self,
        presenter,
        request_domain_refresh: Callable,
        set_is_busy: Callable,
        set_error_message: Callable,
        set_feedback_message: Callable,
    ) -> None:
        self._presenter = presenter
        self._request_domain_refresh = request_domain_refresh
        self._set_is_busy = set_is_busy
        self._set_error_message = set_error_message
        self._set_feedback_message = set_feedback_message

    def _run(self, operation: Callable, success_message: str) -> dict[str, object]:
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def add_time_entry(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.add_time_entry(dict(payload)),
            "Time entry added.",
        )

    def update_time_entry(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.update_time_entry(dict(payload)),
            "Time entry updated.",
        )

    def delete_time_entry(self, entry_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.delete_time_entry(entry_id),
            "Time entry deleted.",
        )

    def submit_period(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.submit_period(dict(payload)),
            "Timesheet period submitted.",
        )

    def approve_period(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.approve_period(dict(payload)),
            "Timesheet period approved.",
        )

    def reject_period(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.reject_period(dict(payload)),
            "Timesheet period rejected.",
        )

    def lock_period(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.lock_period(dict(payload)),
            "Timesheet period locked.",
        )

    def unlock_period(self, payload: dict) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.unlock_period(dict(payload)),
            "Timesheet period unlocked.",
        )

    def bulk_approve_periods(self, period_ids: list) -> dict[str, object]:
        ids = [str(i) for i in (period_ids or [])]
        if not ids:
            return {"ok": False, "message": "No periods selected."}
        return self._run(
            lambda: [self._presenter.approve_period({"periodId": i}) for i in ids],
            f"{len(ids)} period(s) approved.",
        )

    def bulk_reject_periods(self, period_ids: list) -> dict[str, object]:
        ids = [str(i) for i in (period_ids or [])]
        if not ids:
            return {"ok": False, "message": "No periods selected."}
        return self._run(
            lambda: [self._presenter.reject_period({"periodId": i}) for i in ids],
            f"{len(ids)} period(s) rejected.",
        )

__all__ = ["TimesheetsMutationHandler"]
