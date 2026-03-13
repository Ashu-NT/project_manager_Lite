from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.modules.project_management.dashboard.styles import dashboard_card_style
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class ChartWidget(QWidget):
    _PREFERRED_HEIGHT = 252
    _MINIMUM_HEIGHT = 220
    _MAXIMUM_HEIGHT = 292
    _CANVAS_MINIMUM_HEIGHT = 184
    _CANVAS_MAXIMUM_HEIGHT = 228

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._fig: Figure
        self._ax: Axes
        self._fig, self._ax = plt.subplots(figsize=(5.8, 2.4))
        self._canvas: FigureCanvas = FigureCanvas(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM, CFG.SPACING_XS)
        layout.setSpacing(CFG.SPACING_XS)
        self._title = QLabel(title)
        self._title.setStyleSheet(CFG.CHART_TITLE_STYLE)
        layout.addWidget(self._title)
        layout.addWidget(self._canvas)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._canvas.setMinimumHeight(self._CANVAS_MINIMUM_HEIGHT)
        self._canvas.setMaximumHeight(self._CANVAS_MAXIMUM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(self._MINIMUM_HEIGHT)
        self.setMaximumHeight(self._MAXIMUM_HEIGHT)
        self.setStyleSheet(dashboard_card_style())
        self._apply_chart_theme()

    @property
    def ax(self) -> Axes:
        return self._ax

    @property
    def fig(self) -> Figure:
        return self._fig

    def sizeHint(self) -> QSize:
        return QSize(560, self._PREFERRED_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, self._MINIMUM_HEIGHT)

    def redraw(self) -> None:
        self._apply_chart_theme()
        self._canvas.draw_idle()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fig.tight_layout()
        self._apply_chart_theme()
        self._canvas.draw_idle()

    def _apply_chart_theme(self) -> None:
        self._fig.patch.set_facecolor(CFG.COLOR_BG_SURFACE)
        self._ax.set_facecolor(CFG.COLOR_BG_SURFACE_ALT)
        self._ax.title.set_color(CFG.COLOR_TEXT_PRIMARY)
        self._ax.xaxis.label.set_color(CFG.COLOR_TEXT_SECONDARY)
        self._ax.yaxis.label.set_color(CFG.COLOR_TEXT_SECONDARY)
        self._ax.tick_params(colors=CFG.COLOR_TEXT_SECONDARY, labelsize=8)
        for spine in self._ax.spines.values():
            spine.set_color(CFG.COLOR_BORDER)
        for gridline in (*self._ax.get_xgridlines(), *self._ax.get_ygridlines()):
            gridline.set_color(CFG.COLOR_BORDER_STRONG)
            gridline.set_alpha(0.35)
        for text in self._ax.texts:
            if str(text.get_color()).strip().lower() in {"black", "#000000", "#000", "k"}:
                text.set_color(CFG.COLOR_TEXT_PRIMARY)
        legend = self._ax.get_legend()
        if legend is not None:
            frame = legend.get_frame()
            frame.set_facecolor(CFG.COLOR_BG_SURFACE)
            frame.set_edgecolor(CFG.COLOR_BORDER)
            for text in legend.get_texts():
                text.set_color(CFG.COLOR_TEXT_SECONDARY)
        self._canvas.setStyleSheet(f"background-color: {CFG.COLOR_BG_SURFACE}; border: none;")


__all__ = ["ChartWidget"]
