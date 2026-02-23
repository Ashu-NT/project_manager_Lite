from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.styles.ui_config import UIConfig as CFG


class KpiCard(QWidget):
    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        color: str = "#4a90e2",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM, CFG.SPACING_XS)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)

        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=color))

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
            layout.addWidget(lbl_sub)

        layout.addStretch()

        self.setStyleSheet(
            """
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """
        )


class ChartWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._fig, self._ax = plt.subplots()
        self._canvas = FigureCanvas(self._fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_XS, CFG.SPACING_SM, CFG.SPACING_XS)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(CFG.CHART_TITLE_STYLE)

        layout.addWidget(lbl_title)
        layout.addWidget(self._canvas)

        self._canvas.setSizePolicy(CFG.GROW, CFG.GROW)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """
        )

    @property
    def ax(self):
        return self._ax

    @property
    def fig(self):
        return self._fig

    def redraw(self):
        self._canvas.draw()


__all__ = ["KpiCard", "ChartWidget"]
