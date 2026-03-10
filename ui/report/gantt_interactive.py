from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
)

from ui.styles.ui_config import UIConfig as CFG


class _InteractiveGanttBar(QGraphicsRectItem):
    def __init__(
        self,
        *,
        task_id: str,
        day_offset: int,
        day_width: int,
        width_px: int,
        y: int,
        color: QColor,
        movable: bool,
        on_shift,
    ) -> None:
        super().__init__(0, 0, width_px, 22)
        self._task_id = task_id
        self._day_offset = int(day_offset)
        self._day_width = max(1, int(day_width))
        self._on_shift = on_shift
        self.setPos(self._day_offset * self._day_width, y)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120)))
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, bool(movable))
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, bool(movable))
        self.setCursor(Qt.OpenHandCursor if movable else Qt.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.flags() & QGraphicsRectItem.ItemIsMovable:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor if self.flags() & QGraphicsRectItem.ItemIsMovable else Qt.ArrowCursor)
        snapped = max(0, int(round(self.x() / self._day_width)))
        self.setX(snapped * self._day_width)
        shift_days = int(snapped - self._day_offset)
        self._on_shift(self._task_id, shift_days)


class GanttInteractiveMixin:
    DAY_WIDTH = 22
    LABEL_GUTTER = 280
    ROW_HEIGHT = 28

    def _init_interactive_widgets(self, parent_layout) -> None:
        self._interactive_pending_shifts: dict[str, int] = {}
        self.interactive_hint = QLabel(
            "Interactive mode: drag bars horizontally to shift task start dates, then apply changes."
        )
        self.interactive_hint.setWordWrap(True)
        self.interactive_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        parent_layout.addWidget(self.interactive_hint)

        self.interactive_scene = QGraphicsScene(self)
        self.interactive_view = QGraphicsView(self.interactive_scene)
        self.interactive_view.setMinimumHeight(220)
        self.interactive_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.interactive_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        parent_layout.addWidget(self.interactive_view)

        interactive_btns = QHBoxLayout()
        self.btn_reset_changes = QPushButton("Reset Drag Changes")
        self.btn_apply_changes = QPushButton("Apply Drag Changes")
        self.lbl_pending = QLabel("No pending drag changes.")
        self.lbl_pending.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.lbl_pending.setWordWrap(True)
        for btn in (self.btn_reset_changes, self.btn_apply_changes):
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        interactive_btns.addWidget(self.btn_reset_changes)
        interactive_btns.addWidget(self.btn_apply_changes)
        interactive_btns.addWidget(self.lbl_pending, 1)
        parent_layout.addLayout(interactive_btns)

        self.btn_apply_changes.clicked.connect(self._apply_drag_changes)
        self.btn_reset_changes.clicked.connect(self._reset_drag_changes)

    def _build_interactive_timeline(self, *, error_text: str | None = None) -> None:
        self.interactive_scene.clear()
        self._interactive_pending_shifts = {}
        self._sync_pending_label()

        if error_text:
            self.interactive_scene.addText(f"Interactive timeline unavailable: {error_text}")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            return

        if not self._can_edit:
            self.interactive_hint.setText(
                "Interactive editing is read-only in this session. "
                "Task management permission is required."
            )
        bars = self._reporting_service.get_gantt_data(self._project_id)
        dated = [b for b in bars if b.start and b.end]
        if not dated:
            self.interactive_scene.addText("No schedulable tasks available for drag editing.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            return

        timeline_start = min(b.start for b in dated if b.start)
        timeline_end = max(b.end for b in dated if b.end)
        days_span = max(1, (timeline_end - timeline_start).days + 1)

        axis_text = QGraphicsSimpleTextItem(
            f"Timeline: {timeline_start.isoformat()} -> {timeline_end.isoformat()} ({days_span} days)"
        )
        axis_text.setBrush(QBrush(QColor(CFG.COLOR_TEXT_SECONDARY)))
        axis_text.setPos(0, 0)
        self.interactive_scene.addItem(axis_text)

        sorted_bars = sorted(dated, key=lambda b: (b.start, b.name.lower()))
        for row, bar in enumerate(sorted_bars):
            if not bar.start or not bar.end:
                continue
            y = 24 + row * self.ROW_HEIGHT
            start_offset = max(0, (bar.start - timeline_start).days)
            duration_days = max(1, (bar.end - bar.start).days + 1)
            width = duration_days * self.DAY_WIDTH

            label = QGraphicsSimpleTextItem(bar.name)
            label.setBrush(QBrush(QColor(CFG.COLOR_TEXT_PRIMARY)))
            label.setPos(4, y)
            self.interactive_scene.addItem(label)

            color = QColor(CFG.COLOR_WARNING if bar.is_critical else CFG.COLOR_ACCENT)
            bar_item = _InteractiveGanttBar(
                task_id=bar.task_id,
                day_offset=(self.LABEL_GUTTER // self.DAY_WIDTH) + start_offset,
                day_width=self.DAY_WIDTH,
                width_px=width,
                y=y,
                color=color,
                movable=self._can_edit,
                on_shift=self._on_bar_shift,
            )
            bar_item.setToolTip(
                f"{bar.name}\n{bar.start.isoformat()} -> {bar.end.isoformat()}\nDrag to shift schedule."
            )
            self.interactive_scene.addItem(bar_item)

        width = self.LABEL_GUTTER + days_span * self.DAY_WIDTH + 180
        height = 48 + len(sorted_bars) * self.ROW_HEIGHT
        self.interactive_scene.setSceneRect(0, 0, width, max(260, height))
        self.btn_apply_changes.setEnabled(False)
        self.btn_reset_changes.setEnabled(False)

    def _on_bar_shift(self, task_id: str, shift_days: int) -> None:
        normalized_shift = int(shift_days)
        if normalized_shift == 0:
            self._interactive_pending_shifts.pop(task_id, None)
        else:
            self._interactive_pending_shifts[task_id] = normalized_shift
        self._sync_pending_label()

    def _sync_pending_label(self) -> None:
        if not self._interactive_pending_shifts:
            self.lbl_pending.setText("No pending drag changes.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            return
        tasks = len(self._interactive_pending_shifts)
        self.lbl_pending.setText(
            f"Pending drag edits: {tasks} task(s). Click Apply Drag Changes to commit."
        )
        self.btn_apply_changes.setEnabled(self._can_edit)
        self.btn_reset_changes.setEnabled(True)

    def _reset_drag_changes(self) -> None:
        self._build_interactive_timeline()

    def _apply_drag_changes(self) -> None:
        if not self._interactive_pending_shifts:
            return
        if self._task_service is None:
            QMessageBox.warning(self, "Interactive Gantt", "Task service is unavailable.")
            return
        failures: list[str] = []
        applied = 0
        for task_id, shift_days in list(self._interactive_pending_shifts.items()):
            task = self._task_service.get_task(task_id)
            if task is None or task.start_date is None:
                failures.append(task_id)
                continue
            duration = task.duration_days
            if duration is None:
                if task.end_date and task.start_date:
                    duration = max(1, (task.end_date - task.start_date).days + 1)
                else:
                    duration = 1
            try:
                self._task_service.update_task(
                    task_id=task.id,
                    start_date=task.start_date + timedelta(days=shift_days),
                    duration_days=duration,
                )
                applied += 1
            except Exception:
                failures.append(task.name or task.id)

        self._interactive_pending_shifts.clear()
        self._load_image()
        if failures:
            preview = ", ".join(failures[:5]) + ("..." if len(failures) > 5 else "")
            QMessageBox.warning(
                self,
                "Interactive Gantt",
                f"Applied {applied} task update(s). Failed for {len(failures)} task(s): {preview}",
            )
            return
        QMessageBox.information(self, "Interactive Gantt", f"Applied {applied} drag edit(s).")


__all__ = ["GanttInteractiveMixin"]

