from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QInputDialog

from ui.dashboard.tab import DashboardTab
from ui.shared.incident_support import emit_error_event, message_with_incident
from ui.shared.async_job import CancelToken, JobUiConfig, start_async_job
from ui.shared.worker_services import worker_service_scope


def run_generate_baseline_async(tab:DashboardTab) -> None:
    proj_id, _ = tab._current_project_id_and_name()
    if not proj_id:
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


def run_refresh_dashboard_async(tab: DashboardTab, *, show_progress: bool = False) -> None:
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
            data = services["dashboard_service"].get_dashboard_data(proj_id, baseline_id=baseline_id)
            token.raise_if_cancelled()
            return data

    def _on_success(data) -> None:
        tab._current_data = data
        tab._update_summary(proj_name, data)
        tab._update_kpis(data)
        tab._update_burndown_chart(data)
        tab._update_resource_chart(data)
        tab._update_alerts(data)
        if hasattr(tab, "_refresh_conflicts"):
            tab._refresh_conflicts(proj_id)
        tab._update_upcoming(data)
        tab._update_evm(data)

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


__all__ = [
    "run_generate_baseline_async",
    "run_refresh_dashboard_async",
]
