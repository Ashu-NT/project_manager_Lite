from __future__ import annotations
from PySide6.QtWidgets import QMessageBox
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from core.modules.project_management.reporting.api import generate_evm_png, generate_excel_report, generate_gantt_png, generate_pdf_report
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.reporting import ReportingService
from src.core.modules.project_management.application.tasks import TaskService
from src.ui.shared.widgets.guards import can_execute_governed_action, has_permission
from ui.modules.project_management.report.action_helpers import ReportActionHelpersMixin
from ui.modules.project_management.report.dialogs import (
    BaselineCompareDialog,
    CriticalPathDialog,
    EvmReportDialog,
    FinanceReportDialog,
    GanttPreviewDialog,
    KPIReportDialog,
    PerformanceVarianceDialog,
    ResourceLoadDialog,
)


class ReportActionsMixin(ReportActionHelpersMixin):
    _reporting_service: ReportingService
    _finance_service: FinanceService | None
    _task_service: TaskService | None
    _user_session: object | None

    def load_kpis(self) -> None:
        selected = self._require_project("Load KPIs")
        if not selected:
            return
        project_id, _ = selected
        KPIReportDialog(self, self._reporting_service, project_id).exec()

    def show_gantt(self) -> None:
        session = getattr(self, "_user_session", None)
        can_edit = has_permission(session, "task.manage")
        can_open_interactive = can_execute_governed_action(
            user_session=session,
            manage_permission="task.manage",
            governance_action="task.update",
        )
        self._open_dialog(
            "Show Gantt",
            "Gantt",
            lambda project_id, project_name: GanttPreviewDialog(
                self,
                self._reporting_service,
                project_id,
                project_name,
                task_service=getattr(self, "_task_service", None),
                can_edit=can_edit,
                can_open_interactive=can_open_interactive,
            ),
        )

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

__all__ = ["ReportActionsMixin"]
