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
        result = run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )
        if result.get("conflict"):
            self._request_domain_refresh()
        return result

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

__all__ = ["TimesheetsMutationHandler"]
