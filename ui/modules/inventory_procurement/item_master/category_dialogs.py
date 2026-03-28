from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.modules.inventory_procurement.domain import InventoryItemCategory
from ui.platform.shared.code_generation import CodeFieldWidget


_CATEGORY_TYPES = (
    "CONSUMABLE",
    "SPARE",
    "EQUIPMENT",
    "TOOL",
    "CHEMICAL",
    "MATERIAL",
    "SERVICE",
    "OTHER",
)


class InventoryItemCategoryEditDialog(QDialog):
    def __init__(
        self,
        *,
        category: InventoryItemCategory | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._category = category
        self.setWindowTitle("Edit Item Category" if category is not None else "New Item Category")
        self.resize(520, 420)
        self._setup_ui()
        self._load_category()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Govern inventory classifications like consumables, spares, and equipment while marking which categories can flow into project and maintenance use."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.category_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.category_code_field = CodeFieldWidget(
            prefix="CAT",
            line_edit=self.category_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.category_type_combo = QComboBox()
        self.category_type_combo.addItems(_CATEGORY_TYPES)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Short category description or operating intent.")
        self.is_equipment_check = QCheckBox("Equipment-ready classification")
        self.supports_project_usage_check = QCheckBox("Available for project resource planning")
        self.supports_maintenance_usage_check = QCheckBox("Available for maintenance demand and work planning")
        self.is_active_check = QCheckBox("Active")

        form.addRow("Category Code", self.category_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Category Type", self.category_type_combo)
        form.addRow("Description", self.description_edit)
        form.addRow("Equipment", self.is_equipment_check)
        form.addRow("Project Usage", self.supports_project_usage_check)
        form.addRow("Maintenance Usage", self.supports_maintenance_usage_check)
        form.addRow("Status", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_category(self) -> None:
        category = self._category
        if category is None:
            self.category_type_combo.setCurrentText("MATERIAL")
            self.is_active_check.setChecked(True)
            return
        self.category_code_edit.setText(category.category_code)
        self.name_edit.setText(category.name)
        self.category_type_combo.setCurrentText(category.category_type)
        self.description_edit.setPlainText(category.description)
        self.is_equipment_check.setChecked(category.is_equipment)
        self.supports_project_usage_check.setChecked(category.supports_project_usage)
        self.supports_maintenance_usage_check.setChecked(category.supports_maintenance_usage)
        self.is_active_check.setChecked(category.is_active)

    @property
    def category_code(self) -> str:
        return self.category_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def category_type(self) -> str:
        return str(self.category_type_combo.currentText()).strip().upper()

    @property
    def description(self) -> str:
        return self.description_edit.toPlainText().strip()

    @property
    def is_equipment(self) -> bool:
        return self.is_equipment_check.isChecked()

    @property
    def supports_project_usage(self) -> bool:
        return self.supports_project_usage_check.isChecked()

    @property
    def supports_maintenance_usage(self) -> bool:
        return self.supports_maintenance_usage_check.isChecked()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


__all__ = ["InventoryItemCategoryEditDialog"]
