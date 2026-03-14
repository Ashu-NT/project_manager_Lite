from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from ui.platform.shared.styles.ui_config import UIConfig as CFG


class PortfolioScoringTemplateDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Scoring Template")

        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.name_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.name_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.summary_edit = QLineEdit()
        self.summary_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.summary_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.summary_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.strategic_weight = self._weight_spin(default=3)
        self.value_weight = self._weight_spin(default=2)
        self.urgency_weight = self._weight_spin(default=2)
        self.risk_weight = self._weight_spin(default=1)
        self.activate_check = QCheckBox("Make this the active template for new intake items")
        self.activate_check.setChecked(True)

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Name", self.name_edit)
        form.addRow("Summary", self.summary_edit)
        form.addRow("Strategic weight", self.strategic_weight)
        form.addRow("Value weight", self.value_weight)
        form.addRow("Urgency weight", self.urgency_weight)
        form.addRow("Risk weight", self.risk_weight)

        hint = QLabel(
            "Higher strategic, value, and urgency weights increase the composite score. "
            "Risk weight acts as a penalty."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(CFG.INFO_TEXT_STYLE)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(self.activate_check)
        layout.addWidget(buttons)

    @property
    def template_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def template_summary(self) -> str:
        return self.summary_edit.text().strip()

    @staticmethod
    def _weight_spin(*, default: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 9)
        spin.setValue(default)
        spin.setSizePolicy(CFG.INPUT_POLICY)
        spin.setFixedHeight(CFG.INPUT_HEIGHT)
        return spin


__all__ = ["PortfolioScoringTemplateDialog"]
