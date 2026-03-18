from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QTableView, QTableWidget

from core.platform.common.models import Project, Task
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.project import ProjectService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.task import TaskService
from ui.modules.project_management.cost.filters import CostFiltersMixin
from ui.modules.project_management.cost.models import CostTableModel
from ui.modules.project_management.cost.reload_support import (
    CostReloadSnapshot,
    apply_cost_reload_snapshot,
    build_cost_reload_snapshot,
    clear_cost_view,
    reload_project_combo,
)
from ui.platform.shared.async_job import JobUiConfig, start_async_job
from ui.platform.shared.combo import current_data
from ui.platform.shared.worker_services import service_uses_in_memory_sqlite, worker_service_scope


class CostProjectFlowMixin(CostFiltersMixin):
    project_combo: QComboBox
    filter_text: QLineEdit
    filter_type_combo: QComboBox
    filter_task_combo: QComboBox
    model: CostTableModel
    table: QTableView
    tbl_labor_summary: QTableWidget
    lbl_labor_note: QLabel
    lbl_costs_summary: QLabel
    lbl_kpi_budget: QLabel
    lbl_kpi_planned: QLabel
    lbl_kpi_committed: QLabel
    lbl_kpi_actual: QLabel
    lbl_kpi_remaining: QLabel
    _project_service: ProjectService
    _task_service: TaskService
    _cost_service: CostService
    _reporting_service: ReportingService
    _current_project: Project | None
    _project_tasks: list[Task]
    _loaded_cost_snapshot: CostReloadSnapshot | None

    def _load_projects(self):
        projects = reload_project_combo(self)
        self.project_combo.blockSignals(False)
        self._reload_cost_type_filter_options()
        if self.project_combo.count() > 0:
            self._on_project_changed(0)
            return
        self._current_project = None
        self._project_tasks = []
        self._loaded_cost_snapshot = None
        if callable(updater := getattr(self, "_update_cost_header_badges", None)): updater(0, 0)

    def _on_costs_or_tasks_changed(self, project_id: str):
        pid = self._current_project_id()
        if pid != project_id:
            return
        self._project_tasks = self._task_service.list_tasks_for_project(pid)
        self._current_project = self._project_service.get_project(pid)
        self._reload_task_filter_options()
        self.reload_costs(refresh_remote=True)

    def _on_project_changed_event(self, project_id: str):
        prev_pid = self._current_project_id()
        reload_project_combo(self, preferred_project_id=prev_pid)
        pid = self._current_project_id()
        self._current_project = self._project_service.get_project(pid) if pid else None
        self._project_tasks = self._task_service.list_tasks_for_project(pid) if pid else []
        self._reload_cost_type_filter_options()
        self._reload_task_filter_options()
        self.reload_costs(refresh_remote=True)

    def _on_resources_changed(self, _resource_id: str) -> None:
        pid = self._current_project_id()
        if not pid:
            return
        self.reload_costs(refresh_remote=True)

    def _current_project_id(self) -> Optional[str]:
        return current_data(self.project_combo)

    def _on_project_changed(self, index: int):
        pid = self._current_project_id()
        if not pid:
            self._current_project = None
            self._project_tasks = []
            self._loaded_cost_snapshot = None
            clear_cost_view(self)
            if callable(updater := getattr(self, "_update_cost_header_badges", None)): updater(0, 0)
            return
        projects = self._project_service.list_projects()
        self._current_project = next((p for p in projects if p.id == pid), None)
        self._project_tasks = self._task_service.list_tasks_for_project(pid)
        self._reload_cost_type_filter_options()
        self._reload_task_filter_options()
        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)
        if callable(updater := getattr(self, "_update_cost_header_badges", None)): updater(0, 0)
        self.reload_costs(refresh_remote=True)

    def reload_costs(
        self,
        preferred_cost_id: Optional[str] = None,
        *,
        refresh_remote: bool = True,
    ):
        pid = self._current_project_id()
        if not pid:
            self._loaded_cost_snapshot = None
            clear_cost_view(self)
            if callable(sync := getattr(self, "_sync_cost_actions", None)): sync()
            return
        if not refresh_remote:
            apply_cost_reload_snapshot(
                self,
                getattr(self, "_loaded_cost_snapshot", None),
                preferred_cost_id=preferred_cost_id,
            )
            return

        if getattr(self, "_cost_reload_inflight", False):
            setattr(self, "_cost_reload_pending", True)
            setattr(self, "_cost_reload_pending_preferred_cost_id", preferred_cost_id)
            return

        def _set_busy(busy: bool) -> None:
            setattr(self, "_cost_reload_inflight", busy)
            self.btn_refresh_costs.setEnabled(not busy)
            self.project_combo.setEnabled(not busy)
            if busy:
                self.lbl_costs_summary.setText("Loading cost data...")
                self.lbl_labor_note.setText("Loading labor summary...")
            elif bool(getattr(self, "_cost_reload_pending", False)):
                pending_preferred = getattr(self, "_cost_reload_pending_preferred_cost_id", None)
                setattr(self, "_cost_reload_pending", False)
                setattr(self, "_cost_reload_pending_preferred_cost_id", None)
                self.reload_costs(preferred_cost_id=pending_preferred, refresh_remote=True)

        def _load_snapshot(cost_service, reporting_service):
            return build_cost_reload_snapshot(
                self,
                pid,
                cost_service=cost_service,
                reporting_service=reporting_service,
            )

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, "Loading project cost data...")
            with worker_service_scope(getattr(self, "_user_session", None)) as services:
                return _load_snapshot(services["cost_service"], services["reporting_service"])

        def _on_success(snapshot: CostReloadSnapshot) -> None:
            self._loaded_cost_snapshot = snapshot
            apply_cost_reload_snapshot(self, snapshot, preferred_cost_id=preferred_cost_id)  # "Budget warning: Planned" lives in the shared summary formatter.

        def _on_error(message: str) -> None:
            self.lbl_costs_summary.setText("")
            self.lbl_labor_note.setText(f"Labor summary unavailable: {message}")

        if service_uses_in_memory_sqlite(self._cost_service):
            _set_busy(True)
            try:
                snapshot = _load_snapshot(self._cost_service, self._reporting_service)
                _on_success(snapshot)
            except Exception as exc:
                _on_error(str(exc))
            finally:
                _set_busy(False)
            return

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Cost Control",
                label="Refreshing project costs...",
                allow_retry=True,
                show_progress=self.sender() is getattr(self, "btn_refresh_costs", None),
            ),
            work=_work,
            on_success=_on_success,
            on_error=_on_error,
            on_cancel=lambda: None,
            set_busy=_set_busy,
        )

    def _schedule_cost_filter_refresh(self) -> None:
        refresher = getattr(self, "_cost_filter_refresher", None)
        if refresher is None:
            self.reload_costs(refresh_remote=False)
            return
        refresher.trigger()
