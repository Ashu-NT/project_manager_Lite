from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from src.ui.shared.formatting.ui_config import UIConfig as CFG


class PortfolioScenarioDialog(QDialog):
    def __init__(
        self,
        *,
        projects,
        intake_items,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Scenario")

        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.name_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.name_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setMaximum(1_000_000_000)
        self.budget_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.budget_spin.setFixedHeight(CFG.INPUT_HEIGHT)

        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setMaximum(100000)
        self.capacity_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.capacity_spin.setFixedHeight(CFG.INPUT_HEIGHT)

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Name", self.name_edit)
        form.addRow("Budget Limit", self.budget_spin)
        form.addRow("Capacity Limit %", self.capacity_spin)

        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.MultiSelection)
        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.UserRole, project.id)
            self.project_list.addItem(item)

        self.intake_list = QListWidget()
        self.intake_list.setSelectionMode(QListWidget.MultiSelection)
        for intake_item in intake_items:
            item = QListWidgetItem(f"{intake_item.title} ({intake_item.composite_score})")
            item.setData(Qt.UserRole, intake_item.id)
            self.intake_list.addItem(item)

        selection_grid = QGridLayout()
        selection_grid.setHorizontalSpacing(CFG.SPACING_MD)
        selection_grid.setVerticalSpacing(CFG.SPACING_SM)
        selection_grid.addWidget(QLabel("Projects"), 0, 0)
        selection_grid.addWidget(QLabel("Intake Items"), 0, 1)
        selection_grid.addWidget(self.project_list, 1, 0)
        selection_grid.addWidget(self.intake_list, 1, 1)

        hint = QLabel("Select the projects and intake items to include in this saved scenario.")
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
        layout.addLayout(selection_grid, 1)
        layout.addWidget(buttons)
        self.resize(720, 520)

    @property
    def scenario_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def budget_limit(self) -> float | None:
        value = float(self.budget_spin.value())
        return None if value <= 0 else value

    @property
    def capacity_limit_percent(self) -> float | None:
        value = float(self.capacity_spin.value())
        return None if value <= 0 else value

    @property
    def project_ids(self) -> list[str]:
        return self._selected_ids(self.project_list)

    @property
    def intake_item_ids(self) -> list[str]:
        return self._selected_ids(self.intake_list)

    @staticmethod
    def _selected_ids(widget: QListWidget) -> list[str]:
        return [str(item.data(Qt.UserRole) or "") for item in widget.selectedItems()]


__all__ = ["PortfolioScenarioDialog"]
