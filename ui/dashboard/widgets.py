from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtGui import QResizeEvent
from PySide6.QtCore import Qt
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
        layout.setContentsMargins(CFG.SPACING_SM, 4, CFG.SPACING_SM, 4)
        layout.setSpacing(1)
        self._lbl_title: QLabel = QLabel(title)
        self._lbl_title.setStyleSheet(
            f"font-size: 9pt; font-weight: 600; color: {CFG.COLOR_TEXT_SECONDARY};"
        )
        self._lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_value: QLabel = QLabel(value)
        self._lbl_value.setStyleSheet(
            f"font-size: 13pt; font-weight: 800; color: {self._accent};"
        )
        self._lbl_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_sub: QLabel = QLabel(subtitle)
        self._lbl_sub.setStyleSheet(
            f"font-size: 9pt; color: {CFG.COLOR_TEXT_MUTED};"
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
                border-left: 4px solid {self._accent};
                border-radius: 10px;
            }}
            QWidget#kpiStrip QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _sync_height(self) -> None:
        self.setMinimumHeight(80 if self._lbl_sub.isVisible() else 60)

    def set_value(self, value: str) -> None:
        self._lbl_value.setText(value)

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
        self._fig.patch.set_facecolor("white")

    @property
    def ax(self) -> Axes:
        return self._ax

    @property
    def fig(self) -> Figure:
        return self._fig

    def redraw(self):
        self._canvas.draw_idle()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fig.tight_layout()
        self._canvas.draw_idle()

__all__ = ["KpiCard", "ChartWidget"]
