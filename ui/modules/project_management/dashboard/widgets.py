from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.modules.project_management.dashboard.chart_widget import ChartWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG


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
__all__ = ["KpiCard", "ChartWidget"]
