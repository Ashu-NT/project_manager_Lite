from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import QPushButton

from ui.dashboard.styles import dashboard_queue_button_style
from ui.styles.ui_config import UIConfig as CFG


_COUNT_SUFFIX_RE = re.compile(r"^(.+?)\s*\((\d+)\)\s*$")


class DashboardQueueButton(QPushButton):
    def __init__(self, label: str, *, active_variant: str, parent=None):
        super().__init__(label, parent)
        self._label = (label or "").strip() or "Queue"
        self._count = 0
        self._inactive_variant = "success"
        self._active_variant = active_variant
        self._variant = self._inactive_variant
        self.setStyleSheet(dashboard_queue_button_style())
        self.setCursor(Qt.PointingHandCursor)
        font = QFont(CFG.FONT_FAMILY_PRIMARY, CFG.FONT_SIZE_BODY)
        font.setBold(True)
        self.setFont(font)
        super().setText(self._label)

    def set_variants(self, *, active: str, inactive: str = "success") -> None:
        self._active_variant = active
        self._inactive_variant = inactive
        self._variant = inactive if self._count <= 0 else active
        self.update()

    def set_badge(self, count: int, variant: str | None = None) -> None:
        value = max(0, int(count or 0))
        self._count = value
        if variant:
            self._variant = variant
        else:
            self._variant = self._inactive_variant if value == 0 else self._active_variant
        self.update()

    def setText(self, text: str) -> None:  # type: ignore[override]
        raw = (text or "").strip()
        match = _COUNT_SUFFIX_RE.match(raw)
        if match and match.group(1).strip().lower() == self._label.lower():
            self.set_badge(int(match.group(2)))
            super().setText(self._label)
            return
        if raw:
            self._label = raw
        super().setText(self._label)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        text = "99+" if self._count > 99 else str(self._count)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        badge_width = max(18, text_width + 10)
        badge_height = 18
        x = self.width() - badge_width - 10
        y = (self.height() - badge_height) // 2

        bg_hex, fg_hex = _badge_colors(self._variant, enabled=self.isEnabled())
        bg = QColor(bg_hex)
        fg = QColor(fg_hex)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(x, y, badge_width, badge_height, 9, 9)

        painter.setPen(fg)
        badge_font = QFont(self.font())
        badge_font.setPointSize(max(8, badge_font.pointSize() - 1))
        badge_font.setBold(True)
        painter.setFont(badge_font)
        painter.drawText(x, y, badge_width, badge_height, Qt.AlignCenter, text)
        painter.end()


def _badge_colors(variant: str, *, enabled: bool) -> tuple[str, str]:
    if not enabled:
        return CFG.COLOR_BORDER_STRONG, CFG.COLOR_TEXT_MUTED
    palette = {
        "neutral": (CFG.COLOR_BORDER_STRONG, CFG.COLOR_TEXT_PRIMARY),
        "info": (CFG.COLOR_ACCENT, "#FFFFFF"),
        "success": (CFG.COLOR_SUCCESS, "#FFFFFF"),
        "warning": (CFG.COLOR_WARNING, "#FFFFFF"),
        "danger": (CFG.COLOR_DANGER, "#FFFFFF"),
    }
    return palette.get(variant, palette["neutral"])


__all__ = ["DashboardQueueButton"]

