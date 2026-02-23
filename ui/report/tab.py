# ui/report_tab.py
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QMessageBox, QFileDialog,
    QScrollArea,QHeaderView, QTableWidget, QTableWidgetItem, 
   QFormLayout, QDialog
)

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from core.reporting.exporters import (
    generate_excel_report, 
    generate_pdf_report, 
    generate_gantt_png
)
from core.services.project import ProjectService
from core.services.reporting import ReportingService
from core.exceptions import NotFoundError
from ui.styles.ui_config import UIConfig as CFG


class ReportTab(QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        reporting_service: ReportingService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._reporting_service = reporting_service
        
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        
        # --- 1) Project selection --- #
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        
        self.btn_reload_projects = QPushButton(CFG.RELOAD_BUTTON_LABEL)
        
        top_row.addWidget(self.project_combo)
        top_row.addWidget(self.btn_reload_projects)
        top_row.addStretch()
        layout.addLayout(top_row)

        # --- 2) On-screen report actions --- #
        group_on_screen = QGroupBox("On-screen reports")
        group_on_screen.setFont(CFG.GROUPBOX_TITLE_FONT)
        ons_layout = QHBoxLayout(group_on_screen)
        ons_layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )   
        
        self.btn_load_kpi = QPushButton(CFG.SHOW_KPIS_LABEL)
        self.btn_show_gantt = QPushButton(CFG.SHOW_GANTT_LABEL)
        self.btn_show_critical = QPushButton(CFG.SHOW_CRITICAL_PATH_LABEL)
        self.btn_show_resource_load = QPushButton(CFG.SHOW_RESOURCE_LOAD_LABEL)
        
        for btn in [
            self.btn_reload_projects,
            self.btn_load_kpi,
            self.btn_show_gantt,
            self.btn_show_critical,
            self.btn_show_resource_load,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        self.btn_load_kpi.setToolTip("Open a dialog with key project indicators.")
        self.btn_show_gantt.setToolTip("Preview the Gantt chart inside the application.")
        self.btn_show_critical.setToolTip("See the list of critical path tasks.")
        self.btn_show_resource_load.setToolTip("See how busy each resource is on this project.")

        ons_layout.addWidget(self.btn_load_kpi)
        ons_layout.addWidget(self.btn_show_gantt)
        ons_layout.addWidget(self.btn_show_critical)
        ons_layout.addWidget(self.btn_show_resource_load)
        ons_layout.addStretch()

        layout.addWidget(group_on_screen)

        # --- 3) Export actions --- #
        group_export = QGroupBox("Export reports")
        group_export.setFont(CFG.GROUPBOX_TITLE_FONT)
        exp_layout = QHBoxLayout(group_export)
        exp_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.btn_export_gantt = QPushButton(CFG.EXPORT_GANTT_LABEL)
        self.btn_export_excel = QPushButton(CFG.EXPORT_EXCEL_LABEL)
        self.btn_export_pdf = QPushButton(CFG.EXPORT_PDF_LABEL)
        
        for btn in [
            self.btn_export_gantt,
            self.btn_export_excel,
            self.btn_export_pdf,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        self.btn_export_gantt.setToolTip("Save the Gantt chart as a PNG image.")
        self.btn_export_excel.setToolTip("Export KPIs, tasks, and resource load as an Excel workbook.")
        self.btn_export_pdf.setToolTip("Generate a PDF report with KPIs, Gantt chart, and resource load.")

        exp_layout.addWidget(self.btn_export_gantt)
        exp_layout.addWidget(self.btn_export_excel)
        exp_layout.addWidget(self.btn_export_pdf)
        exp_layout.addStretch()

        layout.addWidget(group_export)

        # --- 4) Hint / info label --- #
        info_label = QLabel(
            "Choose a project above, then either preview reports on screen or export them.\n"
            "Calendar settings and task changes will be reflected in all reports."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info_label)

        layout.addStretch()

        # --- Signals --- #
        self.btn_reload_projects.clicked.connect(self._load_projects)

        self.btn_load_kpi.clicked.connect(self.load_kpis)
        self.btn_show_gantt.clicked.connect(self.show_gantt)
        self.btn_show_critical.clicked.connect(self.show_critical_path)
        self.btn_show_resource_load.clicked.connect(self.show_resource_load)

        self.btn_export_gantt.clicked.connect(self.export_gantt_png)
        self.btn_export_excel.clicked.connect(self.export_excel)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
    
    def _load_projects(self):
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)

    def _current_project_id(self) -> str | None:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None
        return self.project_combo.itemData(idx)

    def load_kpis(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Load KPIs", "Please select a project.")
            return
        dlg = KPIReportDialog(self, self._reporting_service, pid)
        dlg.exec()

    def show_gantt(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Show Gantt", "Please select a project.")
            return
        try:
            dlg = GanttPreviewDialog(self, self._reporting_service, pid, name)
            dlg.exec()  
        except NotFoundError as e:
            QMessageBox.warning(self, "Gantt", f"Failed to generate Gantt {str(e)}")
            return

    def show_critical_path(self):
        pid , name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Show Critical Path", "Please select a project.")
            return
        try:
            dlg = CriticalPathDialog(self, self._reporting_service, pid, name)
            dlg.exec() 
        except NotFoundError as e:
            QMessageBox.warning(self, "Critical Path", f"Failed to show critical path {str(e)}")
            return

    def show_resource_load(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Show Resource Load", "Please select a project.")
            return
        try:
            dlg = ResourceLoadDialog(self, self._reporting_service, pid, name)
            dlg.exec()  
        except NotFoundError as e:
            QMessageBox.warning(self, "Resource Load", f"Failed to show resource load {str(e)}")
            return
        
    def _current_project_id_and_name(self):
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None, None
        return self.project_combo.itemData(idx), self.project_combo.currentText()

    def export_gantt_png(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Export Gantt", "Please select a project.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Gantt chart",
            f"{name}_gantt.png",
            "PNG image (*.png)",
        )
        if not path:
            return

        try:
            generate_gantt_png(self._reporting_service, pid, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Gantt: {e}")
            return

        QMessageBox.information(self, "Export Gantt", f"Gantt chart saved to:\n{path}")

    def export_excel(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Export Excel", "Please select a project.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel report",
            f"{name}_report.xlsx",
            "Excel files (*.xlsx)",
        )
        if not path:
            return

        try:
            generate_excel_report(self._reporting_service, pid, path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Excel report: {e}")
            return

        QMessageBox.information(self, "Export Excel", f"Excel report saved to:\n{path}")

    def export_pdf(self):
        pid, name = self._current_project_id_and_name()
        if not pid:
            QMessageBox.information(self, "Export PDF", "Please select a project.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF report",
            f"{name}_report.pdf",
            "PDF files (*.pdf)",
        )
        if not path:
            return

        try:
            generate_pdf_report(self._reporting_service, pid, path)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export PDF report: {e}")
            return

        QMessageBox.information(self, "Export PDF", f"PDF report saved to:\n{path}")
        
class KPIReportDialog(QDialog):
    """
    Shows project KPIs in a user-friendly, grouped layout.
    """
    def __init__(self, parent, reporting_service: ReportingService, project_id: str):
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._project_id = project_id

        self.setWindowTitle("Project KPIs")
        self._setup_ui()

    def _setup_ui(self):
        kpi = self._reporting_service.get_project_kpis(self._project_id)
    
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())

        title = QLabel(f"Project: {kpi.name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        # Section: Schedule
        schedule_label = QLabel("Schedule")
        schedule_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(schedule_label)

        schedule_form = QFormLayout()
   
        schedule_form.addRow("Start date:", QLabel(kpi.start_date.isoformat() if kpi.start_date else "-"))
        schedule_form.addRow("End date:",   QLabel(kpi.end_date.isoformat() if kpi.end_date else "-"))
        schedule_form.addRow("Duration (working days):", QLabel(str(kpi.duration_working_days)))
        layout.addLayout(schedule_form)

        # Section: Tasks
        tasks_label = QLabel("Tasks")
        tasks_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(tasks_label)

        tasks_form = QFormLayout()
        
        tasks_form.addRow("Total tasks:",      QLabel(str(kpi.tasks_total)))
        tasks_form.addRow("Completed:",        QLabel(str(kpi.tasks_completed)))
        tasks_form.addRow("In progress:",      QLabel(str(kpi.tasks_in_progress)))
        tasks_form.addRow("Not started:",      QLabel(str(kpi.tasks_not_started)))
        tasks_form.addRow("Critical tasks:",   QLabel(str(kpi.critical_tasks)))
        tasks_form.addRow("Late tasks:",       QLabel(str(kpi.late_tasks)))
        layout.addLayout(tasks_form)

        # Section: Cost
        cost_label = QLabel("Cost")
        cost_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(cost_label)

        cost_form = QFormLayout()
        cost_form.addRow("Planned cost:", QLabel(f"{kpi.total_planned_cost:.2f}"))
        cost_form.addRow("Actual cost:",  QLabel(f"{kpi.total_actual_cost:.2f}"))
        cost_form.addRow("Cost variance:", QLabel(f"{kpi.cost_variance:.2f}"))
        layout.addLayout(cost_form)

        # Hint
        hint = QLabel(
            "Tip: Use the Excel/PDF export buttons on the Reports tab "
            "to share detailed reports including Gantt and resource load."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"{CFG.INFO_TEXT_STYLE} margin-top: 8px;")
        layout.addWidget(hint)

        for form in [schedule_form, tasks_form, cost_form]:
            form.setLabelAlignment(CFG.ALIGN_LEFT | CFG.ALIGN_CENTER)
            form.setFormAlignment(CFG.ALIGN_TOP)
            form.setHorizontalSpacing(CFG.SPACING_MD)
            form.setVerticalSpacing(CFG.SPACING_SM)
            
            form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
            form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)        

class GanttPreviewDialog(QDialog):
    """
    Shows a visual Gantt chart (PNG) generated by reporting.exporters.
    """
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._project_id = project_id
        self._project_name = project_name

        self.setWindowTitle(f"Gantt - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(  
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_GANTT_WIDTH)
        self.setMinimumHeight(CFG.MIN_GANTT_HEIGHT)

        self.label_info = QLabel(
            "This preview is generated with the same data as the PDF/Excel exports.\n"
            "Use the export buttons if you need high-quality documents."
        )
        self.label_info.setWordWrap(True)
        layout.addWidget(self.label_info)

        # Scrollable image
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in [self.btn_refresh, self.btn_close]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.btn_refresh.clicked.connect(self._load_image)
        self.btn_close.clicked.connect(self.accept)

        self._load_image()

    def _load_image(self):
        try:
            tmpdir = Path(tempfile.gettempdir()) / "pm_gantt_preview"
            tmpdir.mkdir(parents=True, exist_ok=True)
            out_path = tmpdir / f"gantt_{self._project_id}.png"
            generate_gantt_png(self._reporting_service, self._project_id, out_path)
            pix = QPixmap(str(out_path))
            if pix.isNull():
                self.image_label.setText("Unable to load Gantt image.")
            else:
                self.image_label.setPixmap(pix)
        except Exception as e:
            self.image_label.setText(f"Error generating Gantt: {e}")

class CriticalPathDialog(QDialog):
    """
    Shows critical path tasks in a table (no ASCII).
    """
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._project_id = project_id
        self._project_name = project_name

        self.setWindowTitle(f"Critical Path - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_WIDTH)
        self.setMinimumHeight(CFG.MIN_HEIGHT)

        info = QLabel(
            "These tasks are on the critical path. Delays here will delay the whole project."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        critical = self._reporting_service.get_critical_path(self._project_id)

        table = QTableWidget(len(critical), len(CFG.CRITICAL_PATH_HEADERS))
        table.setHorizontalHeaderLabels(CFG.CRITICAL_PATH_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, info in enumerate(critical):
            t = info.task
            start = info.earliest_start
            finish = info.earliest_finish
            dur = (finish - start).days + 1 if (start and finish) else None

            table.setItem(row, 0, QTableWidgetItem(t.name))
            table.setItem(row, 1, QTableWidgetItem(start.isoformat() if start else "-"))
            table.setItem(row, 2, QTableWidgetItem(finish.isoformat() if finish else "-"))
            table.setItem(row, 3, QTableWidgetItem(str(dur) if dur is not None else "-"))
            table.setItem(row, 4, QTableWidgetItem(str(info.total_float_days)))
            table.setItem(row, 5, QTableWidgetItem(getattr(t.status, "value", str(t.status))))

        layout.addWidget(table)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

class ResourceLoadDialog(QDialog):
    """
    Shows a friendly resource load summary (no raw IDs in main columns).
    """
    def __init__(self, parent, reporting_service: ReportingService, project_id: str, project_name: str):
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._project_id = project_id
        self._project_name = project_name

        self.setWindowTitle(f"Resource Load - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(  
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )   
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_WIDTH)
        self.setMinimumHeight(CFG.MIN_HEIGHT)

        info = QLabel(
            "Overview of resource allocation in this project.\n"
            "Values above 100% indicate potential overload."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        rows = self._reporting_service.get_resource_load_summary(self._project_id)

        table = QTableWidget(len(rows), 3)
        table.setHorizontalHeaderLabels(CFG.RESOURCE_LOAD_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for i, r in enumerate(rows):
            # main label: name; ID in tooltip
            name_item = QTableWidgetItem(r.resource_name)
            name_item.setToolTip(f"Resource ID: {r.resource_id}")
            table.setItem(i, 0, name_item)

            alloc_item = QTableWidgetItem(f"{r.total_allocation_percent:.1f}")
            if r.total_allocation_percent > 100.0:
                # simple overload highlight
                alloc_item.setForeground(Qt.red)
            table.setItem(i, 1, alloc_item)

            table.setItem(i, 2, QTableWidgetItem(str(r.tasks_count)))

        layout.addWidget(table)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


