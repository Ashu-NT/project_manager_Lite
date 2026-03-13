from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.dashboard.styles import dashboard_card_style
from ui.styles.ui_config import UIConfig as CFG


class KpiCard(QWidget):
    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        color: str = CFG.COLOR_ACCENT,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._accent: str = color
        self.setObjectName("kpiStrip")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, 6, CFG.SPACING_SM, 6)
        layout.setSpacing(2)
        self._lbl_title: QLabel = QLabel(title)
        self._lbl_title.setStyleSheet(
            f"font-size: 8.5pt; font-weight: 700; letter-spacing: 0.5px; color: {CFG.COLOR_TEXT_SECONDARY};"
        )
        self._lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_value: QLabel = QLabel(value)
        self._lbl_value.setStyleSheet(
            f"font-size: 12.5pt; font-weight: 800; color: {self._accent};"
        )
        self._lbl_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_sub: QLabel = QLabel(subtitle)
        self._lbl_sub.setStyleSheet(
            f"font-size: 8.5pt; color: {CFG.COLOR_TEXT_MUTED};"
        )
        self._lbl_sub.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._lbl_sub.setWordWrap(True)
        self._lbl_sub.setVisible(bool(subtitle))
        layout.addWidget(self._lbl_title)
        layout.addWidget(self._lbl_value)
        layout.addWidget(self._lbl_sub)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._apply_style()
        self._sync_height()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#kpiStrip {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-left: 3px solid {self._accent};
                border-radius: 12px;
            }}
            QWidget#kpiStrip QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _sync_height(self) -> None:
        self.setMinimumHeight(72 if self._lbl_sub.isVisible() else 54)

    def set_value(self, value: str) -> None:
        self._lbl_value.setText(value)

    def set_title(self, title: str) -> None:
        self._lbl_title.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self._lbl_sub.setText(subtitle)
        self._lbl_sub.setVisible(bool(subtitle))
        self._sync_height()


class ChartWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._fig: Figure
        self._ax: Axes
        self._fig, self._ax = plt.subplots()
        self._canvas: FigureCanvas = FigureCanvas(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM, CFG.SPACING_XS)
        layout.setSpacing(CFG.SPACING_XS)
        self._title: QLabel = QLabel(title)
        self._title.setStyleSheet(CFG.CHART_TITLE_STYLE)
        layout.addWidget(self._title)
        layout.addWidget(self._canvas)
        self._canvas.setSizePolicy(CFG.EXPAND_BOTH)
        self.setSizePolicy(CFG.EXPAND_BOTH)
        self.setMinimumHeight(220)
        self.setStyleSheet(dashboard_card_style())
        self._apply_chart_theme()

    @property
    def ax(self) -> Axes:
        return self._ax

    @property
    def fig(self) -> Figure:
        return self._fig

    def redraw(self):
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
            current = str(text.get_color()).strip().lower()
            if current in {"black", "#000000", "#000", "k"}:
                text.set_color(CFG.COLOR_TEXT_PRIMARY)
        legend = self._ax.get_legend()
        if legend is not None:
            frame = legend.get_frame()
            frame.set_facecolor(CFG.COLOR_BG_SURFACE)
            frame.set_edgecolor(CFG.COLOR_BORDER)
            for text in legend.get_texts():
                text.set_color(CFG.COLOR_TEXT_SECONDARY)
        self._canvas.setStyleSheet(f"background-color: {CFG.COLOR_BG_SURFACE}; border: none;")

__all__ = ["KpiCard", "ChartWidget"]
