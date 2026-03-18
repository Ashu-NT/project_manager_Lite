from __future__ import annotations

from datetime import timedelta

from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsSimpleTextItem

from ui.modules.project_management.report.gantt_interactive_bar import _InteractiveGanttBar
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class GanttInteractiveSceneMixin:
    DAY_WIDTH = 22
    LABEL_GUTTER = 280
    ROW_HEIGHT = 30
    _AXIS_ROW_TOP = 44
    _BARS_TOP = 70

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
            self.btn_review_changes.setEnabled(False)
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

        bars = list(getattr(self, "_gantt_bars", []) or [])
        dated = [b for b in bars if b.start and b.end]
        if not dated:
            self.interactive_scene.addText("No schedulable tasks available for interactive editing.")
            self.btn_apply_changes.setEnabled(False)
            self.btn_reset_changes.setEnabled(False)
            self.btn_review_changes.setEnabled(False)
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
        self._sync_undo_button()

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


__all__ = ["GanttInteractiveSceneMixin"]
