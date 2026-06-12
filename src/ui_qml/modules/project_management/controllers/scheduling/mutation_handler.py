from __future__ import annotations

from typing import Callable

from src.ui_qml.modules.project_management.controllers.common import run_mutation

from .activity_log_service import ActivityLogService

class SchedulingMutationHandler:
    def __init__(
        self,
        presenter,
        activity_log_service: ActivityLogService,
        get_project_id: Callable[[], str],
        request_domain_refresh: Callable,
        set_is_busy: Callable,
        set_error_message: Callable,
        set_feedback_message: Callable,
    ) -> None:
        self._presenter = presenter
        self._activity_log_service = activity_log_service
        self._get_project_id = get_project_id
        self._request_domain_refresh = request_domain_refresh
        self._set_is_busy = set_is_busy
        self._set_error_message = set_error_message
        self._set_feedback_message = set_feedback_message

    def _run(
        self,
        operation: Callable,
        success_message: str,
        activity_title: str,
        activity_status: str,
        activity_meta: str,
    ) -> dict[str, object]:
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=lambda: self._after_mutation(
                activity_title, activity_status, activity_meta
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _after_mutation(
        self, activity_title: str, activity_status: str, activity_meta: str
    ) -> None:
        self._activity_log_service.record(
            title=activity_title,
            status_label=activity_status,
            subtitle=self._get_project_id() or "Current project",
            meta_text=activity_meta,
        )
        self._request_domain_refresh()

    def create_baseline(self, payload: dict) -> dict[str, object]:
        name = str(payload.get("name", "") or "Baseline").strip() or "Baseline"
        project_id = self._get_project_id()
        return self._run(
            lambda: self._presenter.create_baseline(dict(payload)),
            "Baseline created.",
            f'Baseline "{name}" saved',
            "Success",
            project_id or "Current project",
        )

    def delete_baseline(self, baseline_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.delete_baseline(baseline_id),
            "Baseline deleted.",
            "Baseline removed",
            "Warning",
            str(baseline_id or ""),
        )

    def submit_baseline(self, baseline_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.submit_baseline(baseline_id),
            "Baseline submitted for approval.",
            "Baseline submitted",
            "Info",
            str(baseline_id or ""),
        )

    def approve_baseline(self, baseline_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.approve_baseline(baseline_id),
            "Baseline approved.",
            "Baseline approved",
            "Success",
            str(baseline_id or ""),
        )

    def reject_baseline(self, baseline_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.reject_baseline(baseline_id),
            "Baseline rejected.",
            "Baseline rejected",
            "Warning",
            str(baseline_id or ""),
        )

    def recalculate_schedule(self) -> dict[str, object]:
        project_id = self._get_project_id()
        return self._run(
            lambda: self._presenter.recalculate_schedule(project_id),
            "Schedule recalculated.",
            "Schedule recalculated",
            "Success",
            project_id or "Current project",
        )

    def create_dependency(self, payload: dict) -> dict[str, object]:
        related_name = str(payload.get("relatedActivityName", "") or "").strip()
        return self._run(
            lambda: self._presenter.create_dependency(dict(payload)),
            "Dependency created.",
            "Dependency created",
            "Success",
            related_name or "Activity relationship saved",
        )

    def update_dependency(self, payload: dict) -> dict[str, object]:
        related_name = str(payload.get("relatedActivityName", "") or "").strip()
        lag_label = str(payload.get("lagDays", "") or "").strip()
        return self._run(
            lambda: self._presenter.update_dependency(dict(payload)),
            "Dependency updated.",
            "Dependency updated",
            "Success",
            f"{related_name or 'Linked activity'} | Lag {lag_label or '0'}",
        )

    def delete_dependency(self, dependency_id: str) -> dict[str, object]:
        return self._run(
            lambda: self._presenter.delete_dependency(dependency_id),
            "Dependency removed.",
            "Dependency removed",
            "Warning",
            str(dependency_id or ""),
        )

__all__ = ["SchedulingMutationHandler"]
