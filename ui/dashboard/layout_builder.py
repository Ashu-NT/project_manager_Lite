from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from ui.styles.ui_config import UIConfig as CFG


class DashboardLayoutDialog(QDialog):
    def __init__(self, parent, *, current_layout: dict[str, object] | None = None) -> None:
        super().__init__(parent)
        self._layout = dict(current_layout or {})
        self.setWindowTitle("Customize Dashboard")
        self._setup_ui()
        self._load_state()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        note = QLabel(
            "Choose visible dashboard widgets and panel balance. "
            "This layout is persisted per user."
        )
        note.setWordWrap(True)
        note.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(note)

        form = QFormLayout()
        form.setSpacing(CFG.SPACING_SM)
        self.chk_summary = QCheckBox("Project Summary")
        self.chk_kpi = QCheckBox("Portfolio KPI Cards")
        self.chk_evm = QCheckBox("EVM Panel")
        self.chk_burndown = QCheckBox("Burndown Chart")
        self.chk_resource = QCheckBox("Resource Load Chart")
        form.addRow(self.chk_summary)
        form.addRow(self.chk_kpi)
        form.addRow(self.chk_evm)
        form.addRow(self.chk_burndown)
        form.addRow(self.chk_resource)
        root.addLayout(form)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Balanced (Recommended)", userData="balanced")
        self.preset_combo.addItem("Cost & EVM", userData="cost_evm")
        self.preset_combo.addItem("Resource Focus", userData="resource_focus")
        root.addWidget(self.preset_combo)

        self.slider_main = QSlider(Qt.Horizontal)
        self.slider_main.setRange(20, 80)
        self.slider_main.setValue(50)
        self.slider_chart = QSlider(Qt.Horizontal)
        self.slider_chart.setRange(20, 80)
        self.slider_chart.setValue(50)
        root.addWidget(QLabel("Main Split (left %):"))
        root.addWidget(self.slider_main)
        root.addWidget(QLabel("Chart Split (burndown %):"))
        root.addWidget(self.slider_chart)

        row = QHBoxLayout()
        self.btn_apply_preset = QPushButton("Apply Preset")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save Layout")
        row.addWidget(self.btn_apply_preset)
        row.addStretch()
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        root.addLayout(row)

        self.btn_apply_preset.clicked.connect(self._apply_preset)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

    def _load_state(self) -> None:
        state = self._layout
        self.chk_summary.setChecked(bool(state.get("show_summary", True)))
        self.chk_kpi.setChecked(bool(state.get("show_kpi", True)))
        self.chk_evm.setChecked(bool(state.get("show_evm", True)))
        self.chk_burndown.setChecked(bool(state.get("show_burndown", True)))
        self.chk_resource.setChecked(bool(state.get("show_resource", True)))
        self.slider_main.setValue(int(state.get("main_left_percent", 50)))
        self.slider_chart.setValue(int(state.get("chart_top_percent", 50)))

    def _apply_preset(self) -> None:
        mode = str(self.preset_combo.currentData() or "balanced")
        if mode in {"cost_evm", "analytics"}:
            self.chk_summary.setChecked(True)
            self.chk_kpi.setChecked(True)
            self.chk_evm.setChecked(True)
            self.chk_burndown.setChecked(False)
            self.chk_resource.setChecked(True)
            self.slider_main.setValue(60)
            self.slider_chart.setValue(35)
            return
        if mode in {"resource_focus", "execution"}:
            self.chk_summary.setChecked(True)
            self.chk_kpi.setChecked(True)
            self.chk_evm.setChecked(False)
            self.chk_burndown.setChecked(False)
            self.chk_resource.setChecked(True)
            self.slider_main.setValue(45)
            self.slider_chart.setValue(30)
            return
        self.chk_summary.setChecked(True)
        self.chk_kpi.setChecked(True)
        self.chk_evm.setChecked(True)
        self.chk_burndown.setChecked(True)
        self.chk_resource.setChecked(True)
        self.slider_main.setValue(50)
        self.slider_chart.setValue(50)

    @property
    def layout_payload(self) -> dict[str, object]:
        return {
            "show_summary": self.chk_summary.isChecked(),
            "show_kpi": self.chk_kpi.isChecked(),
            "show_evm": self.chk_evm.isChecked(),
            "show_burndown": self.chk_burndown.isChecked(),
            "show_resource": self.chk_resource.isChecked(),
            "main_left_percent": int(self.slider_main.value()),
            "chart_top_percent": int(self.slider_chart.value()),
        }


__all__ = ["DashboardLayoutDialog"]
