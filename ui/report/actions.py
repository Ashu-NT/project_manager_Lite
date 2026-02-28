from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from core.exceptions import BusinessRuleError, NotFoundError
from core.reporting.api import generate_evm_png, generate_excel_report, generate_gantt_png, generate_pdf_report
from core.services.finance import FinanceService
from core.services.reporting import ReportingService
from ui.report.dialogs import (
    BaselineCompareDialog,
    CriticalPathDialog,
    EvmReportDialog,
    FinanceReportDialog,
    GanttPreviewDialog,
    KPIReportDialog,
    PerformanceVarianceDialog,
    ResourceLoadDialog,
)
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.shared.incident_support import emit_error_event, message_with_incident
from ui.shared.worker_services import worker_service_scope
class ReportActionsMixin:
    _reporting_service: ReportingService
    _finance_service: FinanceService | None

    def _require_project(self, action_label: str) -> tuple[str, str] | None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, action_label, "Please select a project.")
            return None
        return project_id, (project_name or "project")

    def _open_dialog(self, action_label: str, error_title: str, dialog_factory) -> None:
        selected = self._require_project(action_label)
        if not selected:
            return
        project_id, project_name = selected
        try:
            dialog_factory(project_id, project_name).exec()
        except NotFoundError as exc:
            QMessageBox.warning(self, error_title, f"Failed to show {error_title.lower()}: {exc}")

    def _export_file(
        self,
        *,
        action_label: str,
        save_title: str,
        file_suffix: str,
        file_filter: str,
        success_title: str,
        error_prefix: str,
        error_event_type: str,
        exporter,
        empty_hint: str | None = None,
    ) -> None:
        selected = self._require_project(action_label)
        if not selected:
            return
        project_id, project_name = selected
        path = self._choose_export_path(save_title, f"{project_name}_{file_suffix}", file_filter)
        if not path:
            return

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, f"{success_title}: preparing...")
            with worker_service_scope(getattr(self, "_user_session", None)) as services:
                token.raise_if_cancelled()
                progress(None, f"{success_title}: generating file...")
                out_path = exporter(services, project_id, Path(path))
                token.raise_if_cancelled()
                return Path(out_path)

        def _on_success(exported_path: Path) -> None:
            if empty_hint and (not exported_path.exists() or exported_path.stat().st_size == 0):
                QMessageBox.information(self, success_title, empty_hint)
                return
            QMessageBox.information(self, success_title, f"{success_title} saved to:\n{exported_path}")

        def _on_error(msg: str) -> None:
            incident_id = emit_error_event(
                event_type=error_event_type,
                message=f"{error_prefix}.",
                parent=self,
                data={"project_id": project_id, "path": path, "error": msg},
            )
            QMessageBox.warning(self, "Error", message_with_incident(f"{error_prefix}: {msg}", incident_id))

        start_async_job(
            parent=self,
            ui=JobUiConfig(title=success_title, label=f"{success_title} in progress...", allow_retry=True),
            work=_work,
            on_success=_on_success,
            on_error=_on_error,
            on_cancel=lambda: QMessageBox.information(self, success_title, f"{success_title} canceled."),
        )

    def load_kpis(self) -> None:
        selected = self._require_project("Load KPIs")
        if not selected:
            return
        project_id, _ = selected
        KPIReportDialog(self, self._reporting_service, project_id).exec()

    def show_gantt(self) -> None:
        self._open_dialog("Show Gantt", "Gantt", lambda project_id, project_name: GanttPreviewDialog(self, self._reporting_service, project_id, project_name))

    def show_critical_path(self) -> None:
        self._open_dialog("Show Critical Path", "Critical Path", lambda project_id, project_name: CriticalPathDialog(self, self._reporting_service, project_id, project_name))

    def show_resource_load(self) -> None:
        self._open_dialog("Show Resource Load", "Resource Load", lambda project_id, project_name: ResourceLoadDialog(self, self._reporting_service, project_id, project_name))

    def show_evm(self) -> None:
        selected = self._require_project("Show EVM")
        if not selected:
            return
        project_id, project_name = selected
        try:
            EvmReportDialog(self, self._reporting_service, project_id, project_name).exec()
        except BusinessRuleError as exc:
            if getattr(exc, "code", None) == "NO_BASELINE":
                QMessageBox.information(self, "EVM Analysis", "EVM requires a baseline. Please create a baseline first.")
                return
            QMessageBox.warning(self, "EVM Analysis", f"Failed to generate EVM analysis: {exc}")
        except NotFoundError as exc:
            QMessageBox.warning(self, "EVM Analysis", f"Failed to generate EVM analysis: {exc}")

    def show_performance(self) -> None:
        self._open_dialog("Show Performance", "Performance", lambda project_id, project_name: PerformanceVarianceDialog(self, self._reporting_service, project_id, project_name))

    def show_finance(self) -> None:
        if self._finance_service is None:
            QMessageBox.information(self, "Finance", "Finance service is not available.")
            return
        self._open_dialog(
            "Show Finance",
            "Finance",
            lambda project_id, project_name: FinanceReportDialog(
                self,
                finance_service=self._finance_service,
                project_id=project_id,
                project_name=project_name,
            ),
        )

    def show_baseline_comparison(self) -> None:
        self._open_dialog("Compare Baselines", "Baseline Comparison", lambda project_id, project_name: BaselineCompareDialog(self, self._reporting_service, project_id, project_name))

    def export_gantt_png(self) -> None:
        self._export_file(
            action_label="Export Gantt",
            save_title="Save Gantt chart",
            file_suffix="gantt.png",
            file_filter="PNG image (*.png)",
            success_title="Export Gantt",
            error_prefix="Failed to export Gantt",
            error_event_type="business.export.gantt.error",
            exporter=lambda services, project_id, path: generate_gantt_png(services["reporting_service"], project_id, path),
        )

    def export_evm_png(self) -> None:
        self._export_file(
            action_label="Export EVM",
            save_title="Save EVM chart",
            file_suffix="evm.png",
            file_filter="PNG image (*.png)",
            success_title="Export EVM",
            error_prefix="Failed to export EVM chart",
            error_event_type="business.export.evm.error",
            exporter=lambda services, project_id, path: generate_evm_png(services["reporting_service"], project_id, path),
            empty_hint="No EVM data available for export. Create a baseline and update progress first.",
        )

    def export_excel(self) -> None:
        self._export_file(
            action_label="Export Excel",
            save_title="Save Excel report",
            file_suffix="report.xlsx",
            file_filter="Excel files (*.xlsx)",
            success_title="Export Excel",
            error_prefix="Failed to export Excel report",
            error_event_type="business.export.excel.error",
            exporter=lambda services, project_id, path: generate_excel_report(
                services["reporting_service"],
                project_id,
                path,
                finance_service=services.get("finance_service"),
            ),
        )

    def export_pdf(self) -> None:
        self._export_file(
            action_label="Export PDF",
            save_title="Save PDF report",
            file_suffix="report.pdf",
            file_filter="PDF files (*.pdf)",
            success_title="Export PDF",
            error_prefix="Failed to export PDF report",
            error_event_type="business.export.pdf.error",
            exporter=lambda services, project_id, path: generate_pdf_report(
                services["reporting_service"],
                project_id,
                path,
                finance_service=services.get("finance_service"),
            ),
        )

    def _choose_export_path(self, title: str, suggested_name: str, file_filter: str) -> str | None:
        sanitized_name = self._sanitize_filename(suggested_name)
        path, _ = QFileDialog.getSaveFileName(self, title, sanitized_name, file_filter)
        return path or None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        sanitized = "".join("_" if c in invalid_chars else c for c in filename).strip().strip(".")
        return sanitized or "report"

__all__ = ["ReportActionsMixin"]
