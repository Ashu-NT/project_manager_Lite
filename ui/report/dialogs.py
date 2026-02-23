from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from core.reporting.api import generate_gantt_png
from core.services.reporting import ReportingService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


def _metric_card(title: str, value: str, subtitle: str = "", color: str | None = None) -> QWidget:
    card = QWidget()
    card.setStyleSheet(
        f"""
        QWidget {{
            background-color: {CFG.COLOR_BG_SURFACE};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 10px;
        }}
        """
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
    layout.setSpacing(2)

    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    lbl_value = QLabel(value)
    lbl_value.setStyleSheet(
        CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=color or CFG.COLOR_TEXT_PRIMARY)
    )
    lbl_sub = QLabel(subtitle)
    lbl_sub.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
    lbl_sub.setWordWrap(True)
    lbl_sub.setVisible(bool(subtitle))

    layout.addWidget(lbl_title)
    layout.addWidget(lbl_value)
    layout.addWidget(lbl_sub)
    layout.addStretch()
    return card


def _section_group(title: str, rows: list[tuple[str, str]]) -> QGroupBox:
    group = QGroupBox(title)
    group.setFont(CFG.GROUPBOX_TITLE_FONT)

    form = QFormLayout(group)
    form.setLabelAlignment(CFG.ALIGN_LEFT | CFG.ALIGN_CENTER)
    form.setFormAlignment(CFG.ALIGN_TOP)
    form.setHorizontalSpacing(CFG.SPACING_MD)
    form.setVerticalSpacing(CFG.SPACING_SM)
    form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.DontWrapRows)

    for label, value in rows:
        v = QLabel(value)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(label, v)

    return group


def _setup_dialog_size(dialog: QDialog, min_width: int, min_height: int, width: int, height: int) -> None:
    dialog.setMinimumWidth(min_width)
    dialog.setMinimumHeight(min_height)
    dialog.resize(width, height)


def _soft_brush(hex_color: str, alpha: int) -> QBrush:
    color = QColor(hex_color)
    color.setAlpha(max(0, min(alpha, 255)))
    return QBrush(color)


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
        _setup_dialog_size(self, 860, 540, 980, 680)

        title = QLabel(f"Project KPIs - {kpi.name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            "Snapshot of schedule, task execution, and cost performance for this project."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(subtitle)

        completion_pct = (100.0 * kpi.tasks_completed / kpi.tasks_total) if kpi.tasks_total else 0.0
        variance_color = CFG.COLOR_DANGER if kpi.cost_variance > 0 else CFG.COLOR_SUCCESS

        cards_row = QHBoxLayout()
        cards_row.setSpacing(CFG.SPACING_SM)
        cards_row.addWidget(
            _metric_card(
                "Task Completion",
                f"{completion_pct:.1f}%",
                f"{kpi.tasks_completed} done / {kpi.tasks_total} total",
                CFG.COLOR_ACCENT,
            )
        )
        cards_row.addWidget(
            _metric_card(
                "Critical Tasks",
                str(kpi.critical_tasks),
                "Tasks with zero total float",
                CFG.COLOR_WARNING,
            )
        )
        cards_row.addWidget(
            _metric_card(
                "Late Tasks",
                str(kpi.late_tasks),
                "Tasks currently behind schedule",
                CFG.COLOR_DANGER,
            )
        )
        cards_row.addWidget(
            _metric_card(
                "Cost Variance",
                f"{kpi.cost_variance:.2f}",
                "Actual - Planned",
                variance_color,
            )
        )
        layout.addLayout(cards_row)

        details_row = QHBoxLayout()
        details_row.setSpacing(CFG.SPACING_SM)
        details_row.addWidget(
            _section_group(
                "Schedule",
                [
                    ("Start date:", kpi.start_date.isoformat() if kpi.start_date else "-"),
                    ("End date:", kpi.end_date.isoformat() if kpi.end_date else "-"),
                    (
                        "Duration (working days):",
                        str(kpi.duration_working_days) if kpi.duration_working_days is not None else "-",
                    ),
                ],
            )
        )
        details_row.addWidget(
            _section_group(
                "Task Breakdown",
                [
                    ("Total tasks:", str(kpi.tasks_total)),
                    ("Completed:", str(kpi.tasks_completed)),
                    ("In progress:", str(kpi.tasks_in_progress)),
                    ("Blocked:", str(kpi.task_blocked)),
                    ("Not started:", str(kpi.tasks_not_started)),
                ],
            )
        )
        details_row.addWidget(
            _section_group(
                "Cost Overview",
                [
                    ("Planned:", f"{kpi.total_planned_cost:.2f}"),
                    ("Committed:", f"{kpi.total_committed_cost:.2f}"),
                    ("Actual:", f"{kpi.total_actual_cost:.2f}"),
                    ("Variance:", f"{kpi.cost_variance:.2f}"),
                ],
            )
        )
        layout.addLayout(details_row)

        hint = QLabel(
            "Use Excel/PDF exports from the Reports tab when you need printable reporting packages."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(hint)

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
        _setup_dialog_size(self, 920, 520, 1220, 720)

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
        _setup_dialog_size(self, 920, 520, 1120, 680)

        title = QLabel(f"Critical Path - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        info_label = QLabel(
            "These tasks define the minimum project duration. "
            "Delay on any of them typically delays the entire project."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info_label)

        critical = self._reporting_service.get_critical_path(self._project_id)
        if critical:
            starts = [item.earliest_start for item in critical if item.earliest_start]
            finishes = [item.earliest_finish for item in critical if item.earliest_finish]
            if starts and finishes:
                summary = (
                    f"Critical tasks: {len(critical)} | "
                    f"Path span: {min(starts).isoformat()} to {max(finishes).isoformat()}"
                )
            else:
                summary = f"Critical tasks: {len(critical)}"
        else:
            summary = "No critical tasks identified."
        summary_label = QLabel(summary)
        summary_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        layout.addWidget(summary_label)

        table = QTableWidget(len(critical), len(CFG.CRITICAL_PATH_HEADERS))
        table.setHorizontalHeaderLabels(CFG.CRITICAL_PATH_HEADERS)
        style_table(table)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(CFG.CRITICAL_PATH_HEADERS)):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        for row, item in enumerate(critical):
            task = item.task
            start = item.earliest_start
            finish = item.earliest_finish
            dur = (finish - start).days + 1 if (start and finish) else None
            status_text = str(getattr(task.status, "value", task.status or "-")).replace("_", " ").title()

            cells = [
                QTableWidgetItem(task.name),
                QTableWidgetItem(start.isoformat() if start else "-"),
                QTableWidgetItem(finish.isoformat() if finish else "-"),
                QTableWidgetItem(str(dur) if dur is not None else "-"),
                QTableWidgetItem(str(item.total_float_days)),
                QTableWidgetItem(status_text),
            ]
            cells[3].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cells[4].setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for col, cell in enumerate(cells):
                table.setItem(row, col, cell)

            row_bg = _soft_brush(CFG.COLOR_DANGER, 34)
            for col in range(len(cells)):
                table.item(row, col).setBackground(row_bg)

        if not critical:
            table.setRowCount(1)
            msg = QTableWidgetItem("No critical tasks to display.")
            msg.setForeground(QBrush(QColor(CFG.COLOR_TEXT_MUTED)))
            table.setItem(0, 0, msg)
            for col in range(1, len(CFG.CRITICAL_PATH_HEADERS)):
                table.setItem(0, col, QTableWidgetItem(""))

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
        _setup_dialog_size(self, 900, 520, 1080, 660)

        title = QLabel(f"Resource Load - {self._project_name}")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        layout.addWidget(title)

        info = QLabel(
            "Capacity overview by resource. "
            "Values above 100% indicate over-allocation risk."
        )
        info.setWordWrap(True)
        info.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(info)

        rows = self._reporting_service.get_resource_load_summary(self._project_id)
        overloaded = [r for r in rows if r.total_allocation_percent > 100.0]
        avg_load = (
            sum(r.total_allocation_percent for r in rows) / len(rows) if rows else 0.0
        )

        cards_row = QHBoxLayout()
        cards_row.setSpacing(CFG.SPACING_SM)
        cards_row.addWidget(
            _metric_card(
                "Resources",
                str(len(rows)),
                "Assigned in current project",
                CFG.COLOR_ACCENT,
            )
        )
        cards_row.addWidget(
            _metric_card(
                "Overloaded",
                str(len(overloaded)),
                "Above 100% allocation",
                CFG.COLOR_DANGER,
            )
        )
        cards_row.addWidget(
            _metric_card(
                "Average Load",
                f"{avg_load:.1f}%",
                "Across assigned resources",
                CFG.COLOR_WARNING,
            )
        )
        layout.addLayout(cards_row)

        headers = ["Resource", "Total Allocation (%)", "Tasks", "Status"]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        style_table(table)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setSortingEnabled(True)

        for i, row in enumerate(rows):
            name_item = QTableWidgetItem(row.resource_name)
            name_item.setToolTip(f"Resource ID: {row.resource_id}")
            alloc_item = QTableWidgetItem(f"{row.total_allocation_percent:.1f}%")
            alloc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tasks_item = QTableWidgetItem(str(row.tasks_count))
            tasks_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if row.total_allocation_percent > 120.0:
                status_text, fg, row_bg = "Overloaded", CFG.COLOR_DANGER, _soft_brush(CFG.COLOR_DANGER, 34)
            elif row.total_allocation_percent > 100.0:
                status_text, fg, row_bg = "Risk", CFG.COLOR_WARNING, _soft_brush(CFG.COLOR_WARNING, 34)
            elif row.total_allocation_percent >= 80.0:
                status_text, fg, row_bg = "High", CFG.COLOR_ACCENT, _soft_brush(CFG.COLOR_ACCENT, 32)
            else:
                status_text, fg, row_bg = "Balanced", CFG.COLOR_SUCCESS, _soft_brush(CFG.COLOR_SUCCESS, 32)

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QBrush(QColor(fg)))
            alloc_item.setForeground(QBrush(QColor(fg)))

            table.setItem(i, 0, name_item)
            table.setItem(i, 1, alloc_item)
            table.setItem(i, 2, tasks_item)
            table.setItem(i, 3, status_item)

            for col in range(len(headers)):
                table.item(i, col).setBackground(row_bg)

        if not rows:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("No resource assignments for this project."))
            for col in range(1, len(headers)):
                table.setItem(0, col, QTableWidgetItem(""))

        layout.addWidget(table)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setMinimumHeight(CFG.BUTTON_HEIGHT)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
