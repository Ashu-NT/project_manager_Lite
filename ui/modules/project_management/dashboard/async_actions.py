from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QMessageBox, QInputDialog

from src.core.platform.notifications.domain_events import domain_events
from src.core.modules.project_management.application.dashboard import PORTFOLIO_SCOPE_ID
from src.ui.shared.dialogs.incident_support import emit_error_event, message_with_incident
from src.ui.shared.dialogs.async_job import CancelToken, JobUiConfig, start_async_job
from src.ui.shared.models.worker_services import worker_service_scope


@dataclass(slots=True)
class _DashboardRefreshResult:
    data: object
    conflicts: list[object]
    conflict_error: str | None = None


def run_generate_baseline_async(tab) -> None:
    proj_id, _ = tab._current_project_id_and_name()
    if not proj_id or proj_id == PORTFOLIO_SCOPE_ID:
        return

    name, ok = QInputDialog.getText(
        tab, "Create Baseline", "Baseline name:", text="Baseline"
    )
    if not ok:
        return
    baseline_name = name.strip() or "Baseline"

    def _set_busy(busy: bool) -> None:
        if hasattr(tab, "btn_create_baseline"):
            tab.btn_create_baseline.setEnabled(not busy and getattr(tab, "_can_manage_baselines", True))
        if hasattr(tab, "btn_delete_baseline"):
            tab.btn_delete_baseline.setEnabled(not busy and getattr(tab, "_can_manage_baselines", True))
        if hasattr(tab, "btn_refresh_dashboard"):
            tab.btn_refresh_dashboard.setEnabled(not busy)

    def _work(token:CancelToken, progress):
        token.raise_if_cancelled()
        progress(None, "Creating baseline snapshot...")
        with worker_service_scope(getattr(tab, "_user_session", None)) as services:
            token.raise_if_cancelled()
            baseline = services["baseline_service"].create_baseline(proj_id, baseline_name)
            token.raise_if_cancelled()
            return baseline.id

    def _on_success(_baseline_id: str) -> None:
        tab._load_baselines_for_project(proj_id)
        tab.baseline_combo.setCurrentIndex(0)
        run_refresh_dashboard_async(tab)

    def _on_error(msg: str) -> None:
        incident_id = emit_error_event(
            event_type="business.baseline.create.error",
            message="Baseline creation failed.",
            parent=tab,
            data={"project_id": proj_id, "baseline_name": baseline_name, "error": msg},
        )
        QMessageBox.critical(
            tab,
            "Baseline error",
            message_with_incident(f"Could not create baseline:\n{msg}", incident_id),
        )

    start_async_job(
        parent=tab,
        ui=JobUiConfig(
            title="Create Baseline",
            label="Building baseline from current schedule and costs...",
            allow_retry=True,
        ),
        work=_work,
        on_success=_on_success,
        on_error=_on_error,
        on_cancel=lambda: QMessageBox.information(tab, "Baseline", "Baseline creation canceled."),
        set_busy=_set_busy,
    )


def run_refresh_dashboard_async(tab, *, show_progress: bool = False) -> None:
    proj_id, proj_name = tab._current_project_id_and_name()
    if not proj_id:
        tab._clear_dashboard()
        return

    baseline_id = tab._selected_baseline_id() if hasattr(tab, "baseline_combo") else None
    if bool(getattr(tab, "_dashboard_refresh_inflight", False)):
        setattr(tab, "_dashboard_refresh_pending", True)
        return

    def _set_busy(busy: bool) -> None:
        setattr(tab, "_dashboard_refresh_inflight", busy)
        if hasattr(tab, "btn_refresh_dashboard"):
            tab.btn_refresh_dashboard.setEnabled(not busy)
        if not busy and bool(getattr(tab, "_dashboard_refresh_pending", False)):
            setattr(tab, "_dashboard_refresh_pending", False)
            run_refresh_dashboard_async(tab, show_progress=show_progress)

    def _work(token: CancelToken, progress):
        token.raise_if_cancelled()
        progress(None, "Loading dashboard data...")
        with worker_service_scope(getattr(tab, "_user_session", None)) as services:
            token.raise_if_cancelled()
            if proj_id == PORTFOLIO_SCOPE_ID:
                data = services["dashboard_service"].get_portfolio_data()
                conflicts = []
                conflict_error = None
            else:
                dashboard_service = services["dashboard_service"]
                data = dashboard_service.get_dashboard_data(proj_id, baseline_id=baseline_id)
                token.raise_if_cancelled()
                try:
                    conflicts = dashboard_service.preview_resource_conflicts(
                        proj_id,
                        recalculate=False,
                    )
                    conflict_error = None
                except Exception as exc:  # noqa: BLE001
                    conflicts = []
                    conflict_error = str(exc)
            token.raise_if_cancelled()
            return _DashboardRefreshResult(
                data=data,
                conflicts=conflicts,
                conflict_error=conflict_error,
            )

    def _on_success(result: _DashboardRefreshResult) -> None:
        data = result.data
        tab._current_data = data
        tab._update_summary(proj_name, data)
        tab._update_kpis(data)
        tab._update_burndown_chart(data)
        tab._update_resource_chart(data)
        tab._update_alerts(data)
        if proj_id == PORTFOLIO_SCOPE_ID and hasattr(tab, "_update_conflicts_from_load"):
            overloaded = [
                row
                for row in getattr(data, "resource_load", []) or []
                if float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0) > 100.0
            ]
            tab._current_conflicts = []
            tab._update_conflicts_from_load(overloaded)
            if hasattr(tab, "btn_open_conflicts"):
                tab.btn_open_conflicts.setText(f"Conflicts ({len(overloaded)})")
            if hasattr(tab, "_sync_leveling_buttons"):
                tab._sync_leveling_buttons()
        elif hasattr(tab, "_apply_conflict_state"):
            tab._apply_conflict_state(
                proj_id,
                conflicts=result.conflicts,
                data=data,
                error_text=result.conflict_error,
            )
        tab._update_upcoming(data)
        tab._update_evm(data)
        if hasattr(tab, "_update_portfolio_panel"):
            tab._update_portfolio_panel(data)
        if hasattr(tab, "_update_professional_panels"):
            tab._update_professional_panels(data)
        if hasattr(tab, "_schedule_dashboard_layout_sync"):
            tab._schedule_dashboard_layout_sync()
        elif hasattr(tab, "_sync_dashboard_panel_visibility"):
            tab._sync_dashboard_panel_visibility()

    start_async_job(
        parent=tab,
        ui=JobUiConfig(
            title="Dashboard Refresh",
            label="Refreshing portfolio metrics and charts...",
            allow_retry=True,
            show_progress=show_progress,
        ),
        work=_work,
        on_success=_on_success,
        on_error=lambda _msg: tab._clear_dashboard(),
        on_cancel=lambda: QMessageBox.information(tab, "Dashboard", "Dashboard refresh canceled."),
        set_busy=_set_busy,
    )


def run_preview_conflicts_async(tab, project_id: str, *, show_feedback: bool = False) -> None:
    def _set_busy(busy: bool) -> None:
        if hasattr(tab, "_set_leveling_busy"):
            tab._set_leveling_busy(busy)

    def _work(token: CancelToken, progress):
        token.raise_if_cancelled()
        progress(None, "Reviewing resource conflicts...")
        with worker_service_scope(getattr(tab, "_user_session", None)) as services:
            token.raise_if_cancelled()
            try:
                conflicts = services["dashboard_service"].preview_resource_conflicts(project_id)
                error_text = None
            except Exception as exc:  # noqa: BLE001
                conflicts = []
                error_text = str(exc)
            token.raise_if_cancelled()
            return {"conflicts": conflicts, "error_text": error_text}

    def _on_success(result) -> None:
        if hasattr(tab, "_apply_conflict_state"):
            tab._apply_conflict_state(
                project_id,
                conflicts=result.get("conflicts") or [],
                data=getattr(tab, "_current_data", None),
                error_text=result.get("error_text"),
                show_feedback=show_feedback,
            )

    start_async_job(
        parent=tab,
        ui=JobUiConfig(
            title="Resource Conflicts",
            label="Reviewing project resource conflicts...",
            allow_retry=True,
            show_progress=False,
        ),
        work=_work,
        on_success=_on_success,
        on_error=lambda msg: QMessageBox.warning(tab, "Conflicts", msg),
        on_cancel=lambda: None,
        set_busy=_set_busy,
    )


def run_auto_level_conflicts_async(tab, project_id: str, *, max_iterations: int) -> None:
    def _set_busy(busy: bool) -> None:
        if hasattr(tab, "_set_leveling_busy"):
            tab._set_leveling_busy(busy)

    def _work(token: CancelToken, progress):
        token.raise_if_cancelled()
        progress(None, "Auto-leveling resource conflicts...")
        with worker_service_scope(getattr(tab, "_user_session", None)) as services:
            token.raise_if_cancelled()
            result = services["dashboard_service"].auto_level_overallocations(
                project_id=project_id,
                max_iterations=max_iterations,
                emit_events=False,
            )
            token.raise_if_cancelled()
            return result

    def _on_success(result) -> None:
        if hasattr(tab, "_format_auto_level_result_message"):
            message = tab._format_auto_level_result_message(result)
        else:
            resolved = max(0, int(result.conflicts_before) - int(result.conflicts_after))
            message = (
                f"Conflicts: {result.conflicts_before} -> {result.conflicts_after} "
                f"(resolved {resolved})\n"
                f"Iterations used: {result.iterations}\n"
                f"Tasks shifted: {len(result.actions)}"
            )
        QMessageBox.information(
            tab,
            "Auto-Level Result",
            message,
        )
        domain_events.tasks_changed.emit(project_id)

    start_async_job(
        parent=tab,
        ui=JobUiConfig(
            title="Auto-Level",
            label="Resolving resource overallocations...",
            allow_retry=True,
            show_progress=True,
        ),
        work=_work,
        on_success=_on_success,
        on_error=lambda msg: QMessageBox.warning(tab, "Auto-Level", msg),
        on_cancel=lambda: QMessageBox.information(tab, "Auto-Level", "Auto-level canceled."),
        set_busy=_set_busy,
    )


def run_manual_shift_conflict_async(
    tab,
    project_id: str,
    *,
    task_id: str,
    shift_working_days: int,
    reason: str,
) -> None:
    def _set_busy(busy: bool) -> None:
        if hasattr(tab, "_set_leveling_busy"):
            tab._set_leveling_busy(busy)

    def _work(token: CancelToken, progress):
        token.raise_if_cancelled()
        progress(None, "Applying manual conflict shift...")
        with worker_service_scope(getattr(tab, "_user_session", None)) as services:
            token.raise_if_cancelled()
            services["dashboard_service"].manually_shift_task_for_leveling(
                project_id=project_id,
                task_id=task_id,
                shift_working_days=shift_working_days,
                reason=reason,
                emit_events=False,
            )
            token.raise_if_cancelled()
            return None

    start_async_job(
        parent=tab,
        ui=JobUiConfig(
            title="Manual Shift",
            label="Applying dashboard manual shift...",
            allow_retry=True,
            show_progress=True,
        ),
        work=_work,
        on_success=lambda _result: domain_events.tasks_changed.emit(project_id),
        on_error=lambda msg: QMessageBox.warning(tab, "Manual Shift", msg),
        on_cancel=lambda: QMessageBox.information(tab, "Manual Shift", "Manual shift canceled."),
        set_busy=_set_busy,
    )


__all__ = [
    "run_auto_level_conflicts_async",
    "run_generate_baseline_async",
    "run_manual_shift_conflict_async",
    "run_preview_conflicts_async",
    "run_refresh_dashboard_async",
]
