from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from core.reporting.api import generate_gantt_png
from core.services.reporting import ReportingService
from ui.styles.ui_config import UIConfig as CFG


class KPIReportDialog(QDialog):
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
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())

        title = QLabel(f"Project: {kpi.name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        schedule_label = QLabel("Schedule")
        schedule_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(schedule_label)
        schedule_form = QFormLayout()
        schedule_form.addRow("Start date:", QLabel(kpi.start_date.isoformat() if kpi.start_date else "-"))
        schedule_form.addRow("End date:", QLabel(kpi.end_date.isoformat() if kpi.end_date else "-"))
        schedule_form.addRow("Duration (working days):", QLabel(str(kpi.duration_working_days)))
        layout.addLayout(schedule_form)

        tasks_label = QLabel("Tasks")
        tasks_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(tasks_label)
        tasks_form = QFormLayout()
        tasks_form.addRow("Total tasks:", QLabel(str(kpi.tasks_total)))
        tasks_form.addRow("Completed:", QLabel(str(kpi.tasks_completed)))
        tasks_form.addRow("In progress:", QLabel(str(kpi.tasks_in_progress)))
        tasks_form.addRow("Not started:", QLabel(str(kpi.tasks_not_started)))
        tasks_form.addRow("Critical tasks:", QLabel(str(kpi.critical_tasks)))
        tasks_form.addRow("Late tasks:", QLabel(str(kpi.late_tasks)))
        layout.addLayout(tasks_form)

        cost_label = QLabel("Cost")
        cost_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(cost_label)
        cost_form = QFormLayout()
        cost_form.addRow("Planned cost:", QLabel(f"{kpi.total_planned_cost:.2f}"))
        cost_form.addRow("Actual cost:", QLabel(f"{kpi.total_actual_cost:.2f}"))
        cost_form.addRow("Cost variance:", QLabel(f"{kpi.cost_variance:.2f}"))
        layout.addLayout(cost_form)

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
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_GANTT_WIDTH)
        self.setMinimumHeight(CFG.MIN_GANTT_HEIGHT)

        self.label_info = QLabel(
            "This preview is generated with the same data as the PDF/Excel exports.\n"
            "Use the export buttons if you need high-quality documents."
        )
        self.label_info.setWordWrap(True)
        layout.addWidget(self.label_info)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

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
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_WIDTH)
        self.setMinimumHeight(CFG.MIN_HEIGHT)

        info_label = QLabel("These tasks are on the critical path. Delays here will delay the whole project.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        critical = self._reporting_service.get_critical_path(self._project_id)
        table = QTableWidget(len(critical), len(CFG.CRITICAL_PATH_HEADERS))
        table.setHorizontalHeaderLabels(CFG.CRITICAL_PATH_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, item in enumerate(critical):
            task = item.task
            start = item.earliest_start
            finish = item.earliest_finish
            dur = (finish - start).days + 1 if (start and finish) else None
            table.setItem(row, 0, QTableWidgetItem(task.name))
            table.setItem(row, 1, QTableWidgetItem(start.isoformat() if start else "-"))
            table.setItem(row, 2, QTableWidgetItem(finish.isoformat() if finish else "-"))
            table.setItem(row, 3, QTableWidgetItem(str(dur) if dur is not None else "-"))
            table.setItem(row, 4, QTableWidgetItem(str(item.total_float_days)))
            table.setItem(row, 5, QTableWidgetItem(getattr(task.status, "value", str(task.status))))

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
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
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

        for i, row in enumerate(rows):
            name_item = QTableWidgetItem(row.resource_name)
            name_item.setToolTip(f"Resource ID: {row.resource_id}")
            table.setItem(i, 0, name_item)

            alloc_item = QTableWidgetItem(f"{row.total_allocation_percent:.1f}")
            if row.total_allocation_percent > 100.0:
                alloc_item.setForeground(Qt.red)
            table.setItem(i, 1, alloc_item)
            table.setItem(i, 2, QTableWidgetItem(str(row.tasks_count)))

        layout.addWidget(table)
        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

