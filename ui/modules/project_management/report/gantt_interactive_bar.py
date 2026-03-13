from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem


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


__all__ = ["_InteractiveGanttBar"]
