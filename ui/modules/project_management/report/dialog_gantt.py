from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout

from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.task import TaskService
from ui.modules.project_management.report.dialog_helpers import setup_dialog_size
from ui.modules.project_management.report.gantt_interactive import GanttInteractiveMixin
from ui.modules.project_management.report.gantt_preview_loader import load_gantt_image
from ui.platform.shared.guards import apply_permission_hint
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class GanttPreviewDialog(GanttInteractiveMixin, QDialog):
    def __init__(
        self,
        parent,
        reporting_service: ReportingService,
        project_id: str,
        project_name: str,
        *,
        task_service: TaskService | None = None,
        can_edit: bool = False,
        can_open_interactive: bool = False,
    ):
        super().__init__(parent)
        self._reporting_service: ReportingService = reporting_service
        self._task_service: TaskService | None = task_service
        self._can_edit: bool = bool(can_edit and task_service is not None)
        self._can_open_interactive: bool = bool(can_open_interactive and task_service is not None)
        self._project_id: str = project_id
        self._project_name: str = project_name
        self._raw_pixmap: QPixmap = QPixmap()
        self._gantt_bars = []
        self._fit_mode: bool = True
        self._zoom_factor: float = 1.0
        self._load_inflight = False
        self._load_pending = False
        self.setWindowTitle(f"Gantt - {project_name}")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        setup_dialog_size(self, 920, 520, 1220, 720)

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

        self._init_interactive_widgets(layout)

        btn_row = QHBoxLayout()
        self.btn_fit = QPushButton("Fit Width")
        self.btn_actual_size = QPushButton("100%")
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_in = QPushButton("Zoom +")
        self.btn_open_interactive = QPushButton("Open Interactive")
        self.lbl_zoom = QLabel("Fit width")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in [
            self.btn_fit,
            self.btn_actual_size,
            self.btn_zoom_out,
            self.btn_zoom_in,
            self.btn_open_interactive,
            self.btn_refresh,
            self.btn_close,
        ]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_row.addWidget(self.btn_fit)
        btn_row.addWidget(self.btn_actual_size)
        btn_row.addWidget(self.btn_zoom_out)
        btn_row.addWidget(self.btn_zoom_in)
        btn_row.addWidget(self.btn_open_interactive)
        btn_row.addWidget(self.lbl_zoom)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.btn_fit.clicked.connect(self._set_fit_width)
        self.btn_actual_size.clicked.connect(self._set_actual_size)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_open_interactive.clicked.connect(self._toggle_interactive_panel)
        self.btn_refresh.clicked.connect(self._load_image)
        self.btn_close.clicked.connect(self.accept)
        apply_permission_hint(
            self.btn_open_interactive,
            allowed=self._can_open_interactive,
            missing_permission="task.manage or approval.request",
        )
        self.btn_open_interactive.setEnabled(self._can_open_interactive)
        self._set_interactive_visible(False)
        self._load_image()

    def _toggle_interactive_panel(self) -> None:
        if not self._can_open_interactive:
            return
        visible = not self.interactive_container.isVisible()
        self._set_interactive_visible(visible)
        self.btn_open_interactive.setText("Hide Interactive" if visible else "Open Interactive")

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
        load_gantt_image(self)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._fit_mode:
            self._render_preview()
