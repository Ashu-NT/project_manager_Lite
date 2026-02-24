from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from core.exceptions import BusinessRuleError, NotFoundError
from core.reporting.api import (
    generate_evm_png,
    generate_excel_report,
    generate_gantt_png,
    generate_pdf_report,
)
from core.services.reporting import ReportingService
from ui.report.dialogs import (
    BaselineCompareDialog,
    CriticalPathDialog,
    EvmReportDialog,
    GanttPreviewDialog,
    KPIReportDialog,
    PerformanceVarianceDialog,
    ResourceLoadDialog,
)


class ReportActionsMixin:
    _reporting_service: ReportingService

    def _require_project(self, action_label: str) -> tuple[str, str] | None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, action_label, "Please select a project.")
            return None
        return project_id, (project_name or "project")

    def load_kpis(self) -> None:
        selected = self._require_project("Load KPIs")
        if not selected:
            return
        project_id, _ = selected
        KPIReportDialog(self, self._reporting_service, project_id).exec()

    def show_gantt(self) -> None:
        selected = self._require_project("Show Gantt")
        if not selected:
            return
        project_id, project_name = selected
        try:
            GanttPreviewDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Gantt", f"Failed to generate Gantt {e}")

    def show_critical_path(self) -> None:
        selected = self._require_project("Show Critical Path")
        if not selected:
            return
        project_id, project_name = selected
        try:
            CriticalPathDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Critical Path", f"Failed to show critical path {e}")

    def show_resource_load(self) -> None:
        selected = self._require_project("Show Resource Load")
        if not selected:
            return
        project_id, project_name = selected
        try:
            ResourceLoadDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Resource Load", f"Failed to show resource load {e}")

    def show_evm(self) -> None:
        selected = self._require_project("Show EVM")
        if not selected:
            return
        project_id, project_name = selected
        try:
            EvmReportDialog(self, self._reporting_service, project_id, project_name).exec()
        except BusinessRuleError as e:
            if getattr(e, "code", None) == "NO_BASELINE":
                QMessageBox.information(
                    self,
                    "EVM Analysis",
                    "EVM requires a baseline. Please create a baseline first.",
                )
                return
            QMessageBox.warning(self, "EVM Analysis", f"Failed to generate EVM analysis: {e}")
        except NotFoundError as e:
            QMessageBox.warning(self, "EVM Analysis", f"Failed to generate EVM analysis: {e}")

    def show_performance(self) -> None:
        selected = self._require_project("Show Performance")
        if not selected:
            return
        project_id, project_name = selected
        try:
            PerformanceVarianceDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Performance", f"Failed to generate performance view: {e}")

    def show_baseline_comparison(self) -> None:
        selected = self._require_project("Compare Baselines")
        if not selected:
            return
        project_id, project_name = selected
        try:
            BaselineCompareDialog(self, self._reporting_service, project_id, project_name).exec()
        except NotFoundError as e:
            QMessageBox.warning(self, "Baseline Comparison", f"Failed to compare baselines: {e}")

    def export_gantt_png(self) -> None:
        selected = self._require_project("Export Gantt")
        if not selected:
            return
        project_id, project_name = selected

        path = self._choose_export_path("Save Gantt chart", f"{project_name}_gantt.png", "PNG image (*.png)")
        if not path:
            return

        try:
            generate_gantt_png(self._reporting_service, project_id, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Gantt: {e}")
            return
        QMessageBox.information(self, "Export Gantt", f"Gantt chart saved to:\n{path}")

    def export_evm_png(self) -> None:
        selected = self._require_project("Export EVM")
        if not selected:
            return
        project_id, project_name = selected

        path = self._choose_export_path("Save EVM chart", f"{project_name}_evm.png", "PNG image (*.png)")
        if not path:
            return

        out_path = Path(path)
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass

        try:
            exported = generate_evm_png(self._reporting_service, project_id, out_path)
            exported_path = Path(exported)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export EVM chart: {e}")
            return

        if not exported_path.exists() or exported_path.stat().st_size == 0:
            QMessageBox.information(
                self,
                "Export EVM",
                "No EVM data available for export. Create a baseline and update progress first.",
            )
            return

        QMessageBox.information(self, "Export EVM", f"EVM chart saved to:\n{exported_path}")

    def export_excel(self) -> None:
        selected = self._require_project("Export Excel")
        if not selected:
            return
        project_id, project_name = selected

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
        selected = self._require_project("Export PDF")
        if not selected:
            return
        project_id, project_name = selected

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
