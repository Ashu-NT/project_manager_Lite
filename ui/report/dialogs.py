from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
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
        self._raw_pixmap = QPixmap()
        self._fit_mode = True
        self._zoom_factor = 1.0
        self.setWindowTitle(f"Gantt - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_GANTT_WIDTH)
        self.setMinimumHeight(CFG.MIN_GANTT_HEIGHT)

        title = QLabel(f"Gantt Timeline - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        self.label_info = QLabel(
            "Professional preview generated from live schedule data.\n"
            "Use Fit Width for presentation view, or zoom controls for detailed inspection."
        )
        self.label_info.setWordWrap(True)
        self.label_info.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(self.label_info)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

        btn_row = QHBoxLayout()
        self.btn_fit = QPushButton("Fit Width")
        self.btn_actual_size = QPushButton("100%")
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_in = QPushButton("Zoom +")
        self.lbl_zoom = QLabel("Fit width")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in [
            self.btn_fit,
            self.btn_actual_size,
            self.btn_zoom_out,
            self.btn_zoom_in,
            self.btn_refresh,
            self.btn_close,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_row.addWidget(self.btn_fit)
        btn_row.addWidget(self.btn_actual_size)
        btn_row.addWidget(self.btn_zoom_out)
        btn_row.addWidget(self.btn_zoom_in)
        btn_row.addWidget(self.lbl_zoom)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.btn_fit.clicked.connect(self._set_fit_width)
        self.btn_actual_size.clicked.connect(self._set_actual_size)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_refresh.clicked.connect(self._load_image)
        self.btn_close.clicked.connect(self.accept)
        self._load_image()

    def _set_fit_width(self):
        self._fit_mode = True
        self._render_preview()

    def _set_actual_size(self):
        self._fit_mode = False
        self._zoom_factor = 1.0
        self._render_preview()

    def _zoom_in(self):
        self._fit_mode = False
        self._zoom_factor = min(4.0, self._zoom_factor * 1.2)
        self._render_preview()

    def _zoom_out(self):
        self._fit_mode = False
        self._zoom_factor = max(0.4, self._zoom_factor / 1.2)
        self._render_preview()

    def _render_preview(self):
        if self._raw_pixmap.isNull():
            return

        if self._fit_mode:
            target_width = max(380, self.scroll.viewport().width() - 14)
            pix = self._raw_pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
            self.lbl_zoom.setText("Fit width")
        else:
            target_width = max(380, int(self._raw_pixmap.width() * self._zoom_factor))
            target_height = max(240, int(self._raw_pixmap.height() * self._zoom_factor))
            pix = self._raw_pixmap.scaled(
                target_width,
                target_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.lbl_zoom.setText(f"{int(self._zoom_factor * 100)}%")

        self.image_label.setPixmap(pix)
        self.image_label.resize(pix.size())

    def _load_image(self):
        try:
            tmpdir = Path(tempfile.gettempdir()) / "pm_gantt_preview"
            tmpdir.mkdir(parents=True, exist_ok=True)
            out_path = tmpdir / f"gantt_{self._project_id}.png"
            generate_gantt_png(self._reporting_service, self._project_id, out_path)
            pix = QPixmap(str(out_path))
            if pix.isNull():
                self._raw_pixmap = QPixmap()
                self.image_label.setText("Unable to load Gantt image.")
            else:
                self._raw_pixmap = pix
                bars = self._reporting_service.get_gantt_data(self._project_id)
                dated = [b for b in bars if b.start and b.end]
                critical_count = sum(1 for b in dated if b.is_critical)
                if dated:
                    timeline_start = min(b.start for b in dated if b.start)
                    timeline_end = max(b.end for b in dated if b.end)
                    self.meta_label.setText(
                        f"Tasks: {len(dated)} scheduled | Critical: {critical_count} | "
                        f"Timeline: {timeline_start.isoformat()} to {timeline_end.isoformat()}"
                    )
                else:
                    self.meta_label.setText("No scheduled tasks with valid dates.")
                self._render_preview()
        except Exception as e:
            self.image_label.setText(f"Error generating Gantt: {e}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._fit_mode:
            self._render_preview()


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
