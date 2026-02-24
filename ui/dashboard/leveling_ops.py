from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox, QPushButton, QTableWidget

from core.services.dashboard import DashboardData, DashboardService
from core.services.scheduling.leveling_models import ResourceConflict


class DashboardLevelingOpsMixin:
    conflicts_table: QTableWidget
    btn_auto_level: QPushButton
    btn_manual_shift: QPushButton
    _dashboard_service: DashboardService
    _current_conflicts: list[ResourceConflict]
    _current_data: DashboardData | None

    def _refresh_conflicts(self, project_id: str, *, show_feedback: bool = False) -> None:
        error_text = None
        try:
            conflicts = self._dashboard_service.preview_resource_conflicts(project_id)
        except Exception as exc:
            conflicts = []
            error_text = str(exc)
        self._current_conflicts = conflicts
        if conflicts:
            self._update_conflicts(conflicts)
            if show_feedback:
                QMessageBox.information(
                    self,
                    "Conflicts",
                    f"Found {len(conflicts)} daily resource conflict(s).",
                )
        else:
            data = getattr(self, "_current_data", None)
            if data is None:
                try:
                    data = self._dashboard_service.get_dashboard_data(project_id)
                except Exception:
                    data = None
            overloaded = [
                row
                for row in getattr(data, "resource_load", []) or []
                if float(getattr(row, "total_allocation_percent", 0.0) or 0.0) > 100.0
            ]
            if overloaded and hasattr(self, "_update_conflicts_from_load"):
                self._update_conflicts_from_load(overloaded)
                if show_feedback:
                    QMessageBox.information(
                        self,
                        "Conflicts",
                        (
                            f"No daily conflicts found. Showing {len(overloaded)} "
                            "aggregate overload row(s)."
                        ),
                    )
            else:
                self._update_conflicts([])
                if show_feedback and not error_text:
                    QMessageBox.information(
                        self,
                        "Conflicts",
                        "No daily conflicts detected for this project.",
                    )
        if show_feedback and error_text:
            QMessageBox.warning(self, "Conflicts", f"Could not preview conflicts:\n{error_text}")
        self._sync_leveling_buttons()

    def _preview_conflicts(self) -> None:
        project_id, _ = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Conflicts", "Please select a project.")
            return
        self._refresh_conflicts(project_id, show_feedback=True)

    def _auto_level_conflicts(self) -> None:
        project_id, _ = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Auto-Level", "Please select a project.")
            return
        iterations, ok = QInputDialog.getInt(self, "Auto-Level", "Maximum iterations:", 20, 1, 300, 1)
        if not ok:
            return
        try:
            result = self._dashboard_service.auto_level_overallocations(
                project_id=project_id,
                max_iterations=iterations,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Auto-Level", str(exc))
            return
        self.refresh_dashboard()
        QMessageBox.information(
            self,
            "Auto-Level Result",
            (
                f"Conflicts: {result.conflicts_before} -> {result.conflicts_after}\n"
                f"Iterations: {result.iterations}\n"
                f"Tasks shifted: {len(result.actions)}"
            ),
        )

    def _manual_shift_selected_conflict(self) -> None:
        project_id, _ = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Manual Shift", "Please select a project.")
            return
        row = self.conflicts_table.currentRow()
        if row < 0 or row >= len(self._current_conflicts):
            QMessageBox.information(self, "Manual Shift", "Please select a conflict row first.")
            return
        conflict = self._current_conflicts[row]
        if not conflict.entries:
            QMessageBox.information(self, "Manual Shift", "No tasks available in selected conflict.")
            return

        choices = [f"{e.task_name} ({e.allocation_percent:.0f}%)" for e in conflict.entries]
        selected, ok = QInputDialog.getItem(
            self,
            "Manual Shift",
            "Select task to shift:",
            choices,
            0,
            False,
        )
        if not ok:
            return
        task_id = conflict.entries[choices.index(selected)].task_id

        shift_days, ok = QInputDialog.getInt(self, "Manual Shift", "Shift by working days:", 1, 1, 60, 1)
        if not ok:
            return
        reason = (
            f"Dashboard manual leveling ({conflict.resource_name}, "
            f"{conflict.conflict_date.isoformat()})"
        )
        try:
            self._dashboard_service.manually_shift_task_for_leveling(
                project_id=project_id,
                task_id=task_id,
                shift_working_days=shift_days,
                reason=reason,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Manual Shift", str(exc))
            return
        self.refresh_dashboard()

    def _sync_leveling_buttons(self) -> None:
        has_conflicts = bool(getattr(self, "_current_conflicts", []))
        self.btn_auto_level.setEnabled(has_conflicts)
        self.btn_manual_shift.setEnabled(has_conflicts and self.conflicts_table.currentRow() >= 0)


__all__ = ["DashboardLevelingOpsMixin"]
