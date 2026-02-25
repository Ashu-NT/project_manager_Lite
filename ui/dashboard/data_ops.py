from __future__ import annotations
from PySide6.QtWidgets import QComboBox, QInputDialog, QMessageBox

from core.exceptions import BusinessRuleError
from core.services.baseline import BaselineService
from core.services.dashboard import DashboardData, DashboardService
from core.services.project import ProjectService
from ui.dashboard.access import sync_dashboard_baseline_actions
from ui.shared.combo import current_data_and_text


class DashboardDataOpsMixin:
    project_combo: QComboBox
    baseline_combo: QComboBox
    _project_service: ProjectService
    _dashboard_service: DashboardService
    _baseline_service: BaselineService
    _current_data: DashboardData | None

    def _generate_baseline(self):
        proj_id, _ = self._current_project_id_and_name()
        if not proj_id:
            return

        name, ok = QInputDialog.getText(
            self, "Create Baseline", "Baseline name:", text="Baseline"
        )
        if not ok:
            return

        try:
            self._baseline_service.create_baseline(proj_id, name.strip() or "Baseline")
            self._load_baselines_for_project(proj_id)
            self.baseline_combo.setCurrentIndex(0)
            self.refresh_dashboard()
        except BusinessRuleError as exc:
            QMessageBox.information(self, "Baseline", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Baseline error", f"Could not create baseline:\n{exc}")

    def _on_domain_changed(self, project_id: str):
        current_id, _ = self._current_project_id_and_name()
        if current_id == project_id:
            self.reload_projects()

    def _on_project_catalog_changed(self, _project_id: str):
        # Project create/update/delete must refresh dashboard project selector,
        # even when current selection is a different project.
        self.reload_projects()

    def _on_resources_changed(self, _resource_id: str):
        # Resource rename/rate/status affects dashboard labels and load cards.
        self.refresh_dashboard()

    def _on_baseline_changed(self, project_id: str):
        current_id, _ = self._current_project_id_and_name()
        if current_id != project_id:
            return
        selected_baseline = self._selected_baseline_id()
        self._load_baselines_for_project(project_id)
        idx = self.baseline_combo.findData(selected_baseline) if selected_baseline else -1
        self.baseline_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.refresh_dashboard()

    def _on_project_changed(self, index: int = 0):
        proj_id, _ = self._current_project_id_and_name()
        if proj_id:
            self._load_baselines_for_project(proj_id)
            self.baseline_combo.setCurrentIndex(0)
        self.refresh_dashboard()

    def reload_projects(self):
        previous_id, _ = self._current_project_id_and_name()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        selected_id = None
        if projects:
            if previous_id and any(p.id == previous_id for p in projects):
                selected_id = previous_id
            else:
                selected_id = projects[0].id
            idx = self.project_combo.findData(selected_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
        self.project_combo.blockSignals(False)

        if not projects:
            self.baseline_combo.clear()
            self.baseline_combo.addItem("Latest baseline", userData=None)
            self._clear_dashboard()
        else:
            if selected_id:
                self._load_baselines_for_project(selected_id)
                self.baseline_combo.setCurrentIndex(0)
            self.refresh_dashboard()
        sync_dashboard_baseline_actions(self)

    def _current_project_id_and_name(self):
        return current_data_and_text(self.project_combo)

    def refresh_dashboard(self):
        proj_id, proj_name = self._current_project_id_and_name()
        if not proj_id:
            self._clear_dashboard()
            return
        try:
            baseline_id = self._selected_baseline_id() if hasattr(self, "baseline_combo") else None
            data = self._dashboard_service.get_dashboard_data(proj_id, baseline_id=baseline_id)
            if not hasattr(self, "evm_hint"):
                self.evm_group = self._build_evm_panel()
        except Exception:
            self._clear_dashboard()
            return

        self._current_data = data
        self._update_summary(proj_name, data)
        self._update_kpis(data)
        self._update_burndown_chart(data)
        self._update_resource_chart(data)
        self._update_alerts(data)
        if hasattr(self, "_refresh_conflicts"):
            self._refresh_conflicts(proj_id)
        self._update_upcoming(data)
        self._update_evm(data)

    def _load_baselines_for_project(self, project_id: str):
        self.baseline_combo.blockSignals(True)
        self.baseline_combo.clear()

        baselines = self._baseline_service.list_baselines(project_id)

        self.baseline_combo.addItem("Latest baseline", userData=None)
        for b in baselines:
            label = f"{b.name}  ({b.created_at.strftime('%Y-%m-%d %H:%M')})"
            self.baseline_combo.addItem(label, userData=b.id)

        self.baseline_combo.blockSignals(False)

    def _selected_baseline_id(self) -> str | None:
        idx = self.baseline_combo.currentIndex()
        if idx < 0:
            return None
        return self.baseline_combo.itemData(idx)

    def _delete_selected_baseline(self):
        proj_id, _ = self._current_project_id_and_name()
        if not proj_id:
            return

        baseline_id = self._selected_baseline_id()
        if baseline_id is None:
            QMessageBox.information(
                self,
                "Delete baseline",
                "Select a specific baseline (not 'Latest baseline').",
            )
            return

        label = self.baseline_combo.currentText()
        resp = QMessageBox.question(
            self,
            "Delete baseline",
            f"Delete selected baseline?\n\n{label}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self._baseline_service.delete_baseline(baseline_id)
            self._load_baselines_for_project(proj_id)
            self.baseline_combo.setCurrentIndex(0)
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Delete baseline", f"Could not delete baseline:\n{exc}")
