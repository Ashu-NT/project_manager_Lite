from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMessageBox

from core.exceptions import NotFoundError
from core.reporting.api import generate_excel_report, generate_gantt_png, generate_pdf_report
from core.services.reporting import ReportingService
from ui.report.dialogs import (
    CriticalPathDialog,
    GanttPreviewDialog,
    KPIReportDialog,
    ResourceLoadDialog,
)


class ReportActionsMixin:
    _reporting_service: ReportingService

    def load_kpis(self) -> None:
        project_id, _ = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Load KPIs", "Please select a project.")
            return
        KPIReportDialog(self, self._reporting_service, project_id).exec()

    def show_gantt(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Show Gantt", "Please select a project.")
            return
        try:
            GanttPreviewDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Gantt", f"Failed to generate Gantt {e}")

    def show_critical_path(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Show Critical Path", "Please select a project.")
            return
        try:
            CriticalPathDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Critical Path", f"Failed to show critical path {e}")

    def show_resource_load(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Show Resource Load", "Please select a project.")
            return
        try:
            ResourceLoadDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Resource Load", f"Failed to show resource load {e}")

    def export_gantt_png(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Export Gantt", "Please select a project.")
            return

        path = self._choose_export_path("Save Gantt chart", f"{project_name}_gantt.png", "PNG image (*.png)")
        if not path:
            return

        try:
            generate_gantt_png(self._reporting_service, project_id, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Gantt: {e}")
            return
        QMessageBox.information(self, "Export Gantt", f"Gantt chart saved to:\n{path}")

    def export_excel(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Export Excel", "Please select a project.")
            return

        path = self._choose_export_path("Save Excel report", f"{project_name}_report.xlsx", "Excel files (*.xlsx)")
        if not path:
            return

        try:
            generate_excel_report(self._reporting_service, project_id, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Excel report: {e}")
            return
        QMessageBox.information(self, "Export Excel", f"Excel report saved to:\n{path}")

    def export_pdf(self) -> None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, "Export PDF", "Please select a project.")
            return

        path = self._choose_export_path("Save PDF report", f"{project_name}_report.pdf", "PDF files (*.pdf)")
        if not path:
            return

        try:
            generate_pdf_report(self._reporting_service, project_id, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export PDF report: {e}")
            return
        QMessageBox.information(self, "Export PDF", f"PDF report saved to:\n{path}")

    def _choose_export_path(self, title: str, suggested_name: str, file_filter: str) -> str | None:
        sanitized_name = self._sanitize_filename(suggested_name)
        path, _ = QFileDialog.getSaveFileName(self, title, sanitized_name, file_filter)
        return path or None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        sanitized = "".join("_" if c in invalid_chars else c for c in filename)
        sanitized = sanitized.strip().strip(".")
        return sanitized or "report"


__all__ = ["ReportActionsMixin"]
