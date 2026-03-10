from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.report.gantt_interactive_actions import GanttInteractiveActionsMixin
from ui.report.gantt_interactive_bar import _InteractiveGanttBar
from ui.report.gantt_interactive_scene import GanttInteractiveSceneMixin
from ui.styles.ui_config import UIConfig as CFG


class GanttInteractiveMixin(GanttInteractiveSceneMixin, GanttInteractiveActionsMixin):
    def _init_interactive_widgets(self, parent_layout) -> None:
        self._interactive_pending_edits: dict[str, dict[str, int]] = {}
        self._interactive_show_grid = True
        self._interactive_last_apply_snapshot: list[dict[str, object]] = []

        self.interactive_container = QWidget()
        container_layout = QVBoxLayout(self.interactive_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(CFG.SPACING_SM)

        self.interactive_hint = QLabel(
            "Interactive mode: drag bars to shift start dates and drag the right edge to change duration."
        )
        self.interactive_hint.setWordWrap(True)
        self.interactive_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        container_layout.addWidget(self.interactive_hint)

        self.interactive_scene = QGraphicsScene(self)
        self.interactive_view = QGraphicsView(self.interactive_scene)
        self.interactive_view.setMinimumHeight(260)
        self.interactive_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.interactive_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        container_layout.addWidget(self.interactive_view)

        interactive_btns = QHBoxLayout()
        self.btn_toggle_grid = QPushButton("Grid: On")
        self.btn_toggle_grid.setCheckable(True)
        self.btn_toggle_grid.setChecked(True)
        self.btn_review_changes = QPushButton("Review Changes")
        self.btn_reset_changes = QPushButton("Reset Changes")
        self.btn_apply_changes = QPushButton("Apply Changes")
        self.btn_undo_last_apply = QPushButton("Undo Last Apply")
        self.lbl_pending = QLabel("No pending interactive edits.")
        self.lbl_pending.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.lbl_pending.setWordWrap(True)
        self.lbl_apply_status = QLabel("No applied interactive changes yet.")
        self.lbl_apply_status.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.lbl_apply_status.setWordWrap(True)
        for btn in (
            self.btn_toggle_grid,
            self.btn_review_changes,
            self.btn_reset_changes,
            self.btn_apply_changes,
            self.btn_undo_last_apply,
        ):
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        interactive_btns.addWidget(self.btn_toggle_grid)
        interactive_btns.addWidget(self.btn_review_changes)
        interactive_btns.addWidget(self.btn_reset_changes)
        interactive_btns.addWidget(self.btn_apply_changes)
        interactive_btns.addWidget(self.btn_undo_last_apply)
        interactive_btns.addWidget(self.lbl_pending, 1)
        container_layout.addLayout(interactive_btns)
        container_layout.addWidget(self.lbl_apply_status)

        self.btn_apply_changes.clicked.connect(self._apply_drag_changes)
        self.btn_reset_changes.clicked.connect(self._reset_drag_changes)
        self.btn_toggle_grid.toggled.connect(self._on_grid_toggled)
        self.btn_review_changes.clicked.connect(self._review_pending_changes)
        self.btn_undo_last_apply.clicked.connect(self._undo_last_apply)
        self.btn_undo_last_apply.setEnabled(False)

        parent_layout.addWidget(self.interactive_container)
        self.interactive_container.setVisible(False)


__all__ = ["GanttInteractiveMixin", "_InteractiveGanttBar"]
