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
    QVBoxLayout,
    QWidget,
)

from ui.styles.ui_config import UIConfig as CFG


class _InteractiveGanttBar(QGraphicsRectItem):
    _GRIP_WIDTH = 8

    def __init__(
        self,
        *,
        task_id: str,
        day_width: int,
        min_day_offset: int,
        base_day_offset: int,
        current_day_offset: int,
        base_duration_days: int,
        current_duration_days: int,
        y: int,
        color: QColor,
        movable: bool,
        on_shift,
        on_resize,
    ) -> None:
        width_px = max(1, int(current_duration_days)) * max(1, int(day_width))
        super().__init__(0, 0, width_px, 22)
        self._task_id = task_id
        self._day_width = max(1, int(day_width))
        self._min_day_offset = int(min_day_offset)
        self._base_day_offset = int(base_day_offset)
        self._base_duration_days = max(1, int(base_duration_days))
        self._row_y = int(y)
        self._on_shift = on_shift
        self._on_resize = on_resize
        self._movable = bool(movable)
        self._resizing = False
        self._resize_origin_scene_x = 0.0
        self._resize_origin_days = self._base_duration_days

        self.setPos(int(current_day_offset) * self._day_width, self._row_y)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120)))
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, self._movable)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, self._movable)
        self.setCursor(Qt.OpenHandCursor if self._movable else Qt.ArrowCursor)

        self._grip = QGraphicsRectItem(0, 0, 0, 0, self)
        self._grip.setBrush(QBrush(QColor("#FFFFFF")))
        self._grip.setPen(QPen(QColor("#C0C0C0")))
        self._sync_grip()

    def _sync_grip(self) -> None:
        width = self.rect().width()
        self._grip.setRect(max(0, width - self._GRIP_WIDTH), 0, self._GRIP_WIDTH, 22)

    def _is_resize_hit(self, x: float) -> bool:
        return bool(self._movable and x >= self.rect().width() - self._GRIP_WIDTH - 1)

    def _set_duration_days(self, days: int) -> None:
        normalized = max(1, int(days))
        self.setRect(0, 0, normalized * self._day_width, 22)
        self._sync_grip()

    def _current_duration_days(self) -> int:
        return max(1, int(round(self.rect().width() / self._day_width)))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._is_resize_hit(event.pos().x()):
            self._resizing = True
            self._resize_origin_scene_x = float(event.scenePos().x())
            self._resize_origin_days = self._current_duration_days()
            self.setCursor(Qt.SizeHorCursor)
            event.accept()
            return
        if self._movable:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._resizing:
            delta_days = int(round((event.scenePos().x() - self._resize_origin_scene_x) / self._day_width))
            self._set_duration_days(self._resize_origin_days + delta_days)
            event.accept()
            return
        super().mouseMoveEvent(event)
        self.setY(self._row_y)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._resizing:
            snapped_days = self._current_duration_days()
            self._set_duration_days(snapped_days)
            self._on_resize(self._task_id, int(snapped_days - self._base_duration_days))
            self._resizing = False
            self.setCursor(Qt.OpenHandCursor if self._movable else Qt.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor if self._movable else Qt.ArrowCursor)
        snapped = max(self._min_day_offset, int(round(self.x() / self._day_width)))
        self.setX(snapped * self._day_width)
        self.setY(self._row_y)
        shift_days = int(snapped - self._base_day_offset)
        self._on_shift(self._task_id, shift_days)


class GanttInteractiveMixin:
    DAY_WIDTH = 22
    LABEL_GUTTER = 280
    ROW_HEIGHT = 30
    _AXIS_ROW_TOP = 44
    _BARS_TOP = 70

    def _init_interactive_widgets(self, parent_layout) -> None:
        self._interactive_pending_edits: dict[str, dict[str, int]] = {}
        self._interactive_show_grid = True

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
        self.btn_reset_changes = QPushButton("Reset Changes")
        self.btn_apply_changes = QPushButton("Apply Changes")
        self.lbl_pending = QLabel("No pending interactive edits.")
        self.lbl_pending.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.lbl_pending.setWordWrap(True)
        for btn in (self.btn_toggle_grid, self.btn_reset_changes, self.btn_apply_changes):
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        interactive_btns.addWidget(self.btn_toggle_grid)
        interactive_btns.addWidget(self.btn_reset_changes)
        interactive_btns.addWidget(self.btn_apply_changes)
        interactive_btns.addWidget(self.lbl_pending, 1)
        container_layout.addLayout(interactive_btns)

        self.btn_apply_changes.clicked.connect(self._apply_drag_changes)
        self.btn_reset_changes.clicked.connect(self._reset_drag_changes)
        self.btn_toggle_grid.toggled.connect(self._on_grid_toggled)

        parent_layout.addWidget(self.interactive_container)
        self.interactive_container.setVisible(False)

    def _set_interactive_visible(self, visible: bool) -> None:
        self.interactive_container.setVisible(bool(visible))
        if visible:
            self._build_interactive_timeline(keep_pending=True)

    def _on_grid_toggled(self, enabled: bool) -> None:
        self._interactive_show_grid = bool(enabled)
        self.btn_toggle_grid.setText("Grid: On" if enabled else "Grid: Off")
        self._build_interactive_timeline(keep_pending=True)

    def _build_interactive_timeline(
        self,
        *,
        error_text: str | None = None,
        keep_pending: bool = False,
    ) -> None:
        pending = dict(self._interactive_pending_edits) if keep_pending else {}
        self.interactive_scene.clear()
        self._interactive_pending_edits = pending
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
        else:
            self.interactive_hint.setText(
                "Interactive mode: drag bars to shift start dates and drag the right edge to change duration."
            )

        bars = self._reporting_service.get_gantt_data(self._project_id)
        dated = [b for b in bars if b.start and b.end]
        if not dated:
            self.interactive_scene.addText("No schedulable tasks available for interactive editing.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            return

        timeline_start = min(b.start for b in dated if b.start)
        timeline_end = max(b.end for b in dated if b.end)
        days_span = max(1, (timeline_end - timeline_start).days + 1)
        lane_offset_units = (self.LABEL_GUTTER + self.DAY_WIDTH - 1) // self.DAY_WIDTH
        timeline_origin_x = lane_offset_units * self.DAY_WIDTH

        axis_text = QGraphicsSimpleTextItem(
            f"Timeline: {timeline_start.isoformat()} -> {timeline_end.isoformat()} ({days_span} days)"
        )
        axis_text.setBrush(QBrush(QColor(CFG.COLOR_TEXT_SECONDARY)))
        axis_text.setPos(0, 2)
        self.interactive_scene.addItem(axis_text)

        axis_y = self._AXIS_ROW_TOP
        self.interactive_scene.addLine(
            timeline_origin_x,
            axis_y,
            timeline_origin_x + days_span * self.DAY_WIDTH,
            axis_y,
            QPen(QColor("#7D8793"), 1),
        )

        tick_step = self._tick_step(days_span)
        for day in range(0, days_span + 1, tick_step):
            x = timeline_origin_x + day * self.DAY_WIDTH
            tick_date = timeline_start + timedelta(days=day)
            self.interactive_scene.addLine(
                x,
                axis_y - 4,
                x,
                axis_y + 5,
                QPen(QColor("#7D8793"), 1),
            )
            tick_label = QGraphicsSimpleTextItem(tick_date.strftime("%d %b"))
            tick_label.setBrush(QBrush(QColor(CFG.COLOR_TEXT_SECONDARY)))
            tick_label.setPos(x - 18, axis_y + 6)
            self.interactive_scene.addItem(tick_label)

        sorted_bars = sorted(dated, key=lambda b: (b.start, b.name.lower()))
        rows_height = len(sorted_bars) * self.ROW_HEIGHT
        bars_bottom = self._BARS_TOP + rows_height
        if self._interactive_show_grid:
            for day in range(0, days_span + 1, tick_step):
                x = timeline_origin_x + day * self.DAY_WIDTH
                self.interactive_scene.addLine(
                    x,
                    self._BARS_TOP - 6,
                    x,
                    bars_bottom,
                    QPen(QColor("#E2E6EB"), 1),
                )

        for row, bar in enumerate(sorted_bars):
            if not bar.start or not bar.end:
                continue

            y = self._BARS_TOP + row * self.ROW_HEIGHT
            base_start_offset = max(0, (bar.start - timeline_start).days)
            base_duration_days = max(1, (bar.end - bar.start).days + 1)
            edit = self._interactive_pending_edits.get(bar.task_id, {})
            shift_days = int(edit.get("shift", 0))
            duration_delta = int(edit.get("duration_delta", 0))
            current_day_offset = lane_offset_units + base_start_offset + shift_days
            current_duration_days = max(1, base_duration_days + duration_delta)

            label = QGraphicsSimpleTextItem(bar.name)
            label.setBrush(QBrush(QColor(CFG.COLOR_TEXT_PRIMARY)))
            label.setPos(4, y)
            self.interactive_scene.addItem(label)

            if self._interactive_show_grid:
                self.interactive_scene.addLine(
                    timeline_origin_x,
                    y + 23,
                    timeline_origin_x + days_span * self.DAY_WIDTH,
                    y + 23,
                    QPen(QColor("#F0F2F5"), 1),
                )

            color = QColor(CFG.COLOR_WARNING if bar.is_critical else CFG.COLOR_ACCENT)
            bar_item = _InteractiveGanttBar(
                task_id=bar.task_id,
                day_width=self.DAY_WIDTH,
                min_day_offset=lane_offset_units,
                base_day_offset=lane_offset_units + base_start_offset,
                current_day_offset=current_day_offset,
                base_duration_days=base_duration_days,
                current_duration_days=current_duration_days,
                y=y,
                color=color,
                movable=self._can_edit,
                on_shift=self._on_bar_shift,
                on_resize=self._on_bar_resize,
            )
            bar_item.setToolTip(
                f"{bar.name}\n"
                f"{bar.start.isoformat()} -> {bar.end.isoformat()}\n"
                "Drag bar to shift. Drag right edge to resize."
            )
            self.interactive_scene.addItem(bar_item)

        width = timeline_origin_x + days_span * self.DAY_WIDTH + 220
        height = max(300, bars_bottom + 24)
        self.interactive_scene.setSceneRect(0, 0, width, height)
        self._sync_pending_label()

    @staticmethod
    def _tick_step(days_span: int) -> int:
        if days_span <= 21:
            return 1
        if days_span <= 120:
            return 7
        if days_span <= 360:
            return 14
        return 30

    def _upsert_pending_edit(
        self,
        task_id: str,
        *,
        shift_days: int | None = None,
        duration_delta: int | None = None,
    ) -> None:
        edit = dict(self._interactive_pending_edits.get(task_id, {"shift": 0, "duration_delta": 0}))
        if shift_days is not None:
            edit["shift"] = int(shift_days)
        if duration_delta is not None:
            edit["duration_delta"] = int(duration_delta)
        if int(edit.get("shift", 0)) == 0 and int(edit.get("duration_delta", 0)) == 0:
            self._interactive_pending_edits.pop(task_id, None)
        else:
            self._interactive_pending_edits[task_id] = edit
        self._sync_pending_label()

    def _on_bar_shift(self, task_id: str, shift_days: int) -> None:
        self._upsert_pending_edit(task_id, shift_days=int(shift_days))

    def _on_bar_resize(self, task_id: str, duration_delta: int) -> None:
        self._upsert_pending_edit(task_id, duration_delta=int(duration_delta))

    def _sync_pending_label(self) -> None:
        if not self._interactive_pending_edits:
            self.lbl_pending.setText("No pending interactive edits.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            return
        shift_count = sum(
            1
            for edit in self._interactive_pending_edits.values()
            if int(edit.get("shift", 0)) != 0
        )
        duration_count = sum(
            1
            for edit in self._interactive_pending_edits.values()
            if int(edit.get("duration_delta", 0)) != 0
        )
        self.lbl_pending.setText(
            f"Pending edits: {len(self._interactive_pending_edits)} task(s) | "
            f"shift: {shift_count}, duration: {duration_count}"
        )
        self.btn_apply_changes.setEnabled(self._can_edit)
        self.btn_reset_changes.setEnabled(True)

    def _reset_drag_changes(self) -> None:
        self._interactive_pending_edits = {}
        self._build_interactive_timeline(keep_pending=False)

    def _apply_drag_changes(self) -> None:
        if not self._interactive_pending_edits:
            return
        if self._task_service is None:
            QMessageBox.warning(self, "Interactive Gantt", "Task service is unavailable.")
            return

        failures: list[str] = []
        applied = 0
        for task_id, edit in list(self._interactive_pending_edits.items()):
            shift_days = int(edit.get("shift", 0))
            duration_delta = int(edit.get("duration_delta", 0))
            if shift_days == 0 and duration_delta == 0:
                continue

            task = self._task_service.get_task(task_id)
            if task is None or task.start_date is None:
                failures.append(task_id)
                continue

            base_duration = task.duration_days
            if base_duration is None:
                if task.end_date and task.start_date:
                    base_duration = max(1, (task.end_date - task.start_date).days + 1)
                else:
                    base_duration = 1
            new_duration = max(1, int(base_duration) + duration_delta)

            try:
                self._task_service.update_task(
                    task_id=task.id,
                    start_date=task.start_date + timedelta(days=shift_days),
                    duration_days=new_duration,
                )
                applied += 1
            except Exception:
                failures.append(task.name or task.id)

        self._interactive_pending_edits.clear()
        self._load_image()
        if failures:
            preview = ", ".join(failures[:5]) + ("..." if len(failures) > 5 else "")
            QMessageBox.warning(
                self,
                "Interactive Gantt",
                f"Applied {applied} task update(s). Failed for {len(failures)} task(s): {preview}",
            )
            return
        QMessageBox.information(self, "Interactive Gantt", f"Applied {applied} interactive edit(s).")


__all__ = ["GanttInteractiveMixin"]
