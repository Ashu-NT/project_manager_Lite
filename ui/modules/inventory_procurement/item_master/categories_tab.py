from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import ItemCategoryService
from core.modules.inventory_procurement.domain import InventoryItemCategory
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.item_master.category_dialogs import InventoryItemCategoryEditDialog
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


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


class InventoryItemCategoriesTab(QWidget):
    def __init__(
        self,
        *,
        category_service: ItemCategoryService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._category_service = category_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[InventoryItemCategory] = []
        self._setup_ui()
        self.reload_categories()
        domain_events.inventory_item_categories_changed.connect(self._on_categories_changed)
        domain_events.organizations_changed.connect(self._on_categories_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryItemCategoriesHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryItemCategoriesHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)

        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("CATEGORY MASTER")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Item Categories")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Control consumable, spare, and equipment classifications inside inventory while marking which categories can feed project and maintenance demand."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.count_badge = QLabel("0 categories")
        self.count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.active_badge = QLabel("0 active")
        self.active_badge.setStyleSheet(dashboard_meta_chip_style())
        self.equipment_badge = QLabel("0 equipment-ready")
        self.equipment_badge.setStyleSheet(dashboard_meta_chip_style())
        self.access_badge = QLabel("Manage Enabled" if self._can_manage else "Read Only")
        self.access_badge.setStyleSheet(dashboard_meta_chip_style())
        header_layout.addWidget(
            build_inventory_header_badge_widget(
                self.context_badge,
                self.count_badge,
                self.active_badge,
                self.equipment_badge,
                self.access_badge,
            ),
            0,
            Qt.AlignTop | Qt.AlignRight,
        )
        root.addWidget(header)

        controls = QWidget()
        controls.setObjectName("inventoryItemCategoriesControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#inventoryItemCategoriesControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search code, name, description, or category type")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", None)
        for category_type in _CATEGORY_TYPES:
            self.type_filter.addItem(category_type.title(), category_type)
        self.usage_filter = QComboBox()
        self.usage_filter.addItem("All usage", None)
        self.usage_filter.addItem("Equipment-ready", "equipment")
        self.usage_filter.addItem("Project-capable", "project")
        self.usage_filter.addItem("Maintenance-capable", "maintenance")
        self.active_filter = QComboBox()
        self.active_filter.addItem("All statuses", None)
        self.active_filter.addItem("Active only", True)
        self.active_filter.addItem("Inactive only", False)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(self.usage_filter)
        filter_row.addWidget(self.active_filter)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Category")
        self.btn_edit = QPushButton("Edit Category")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_new)
        action_row.addWidget(self.btn_edit)
        action_row.addWidget(self.btn_toggle_active)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)
        root.addWidget(controls)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Code", "Name", "Type", "Equipment", "Projects", "Maintenance", "Active"]
        )
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header_widget = self.table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        content_row.addWidget(self.table, 2)

        detail_card = QWidget()
        detail_card.setObjectName("inventoryItemCategoryDetailCard")
        detail_card.setStyleSheet(
            f"""
            QWidget#inventoryItemCategoryDetailCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        detail_layout.setSpacing(CFG.SPACING_SM)
        detail_title = QLabel("Category Details")
        detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(detail_title)
        self.detail_name = QLabel("Select a category")
        self.detail_name.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        detail_layout.addWidget(self.detail_name)
        self.detail_status = QLabel("-")
        self.detail_status.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        detail_layout.addWidget(self.detail_status)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(CFG.SPACING_MD)
        detail_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.detail_type = QLabel("-")
        self.detail_usage = QLabel("-")
        self.detail_description = QLabel("-")
        self.detail_description.setWordWrap(True)
        detail_grid.addWidget(QLabel("Type"), 0, 0)
        detail_grid.addWidget(self.detail_type, 0, 1)
        detail_grid.addWidget(QLabel("Usage"), 1, 0)
        detail_grid.addWidget(self.detail_usage, 1, 1)
        detail_grid.addWidget(QLabel("Description"), 2, 0)
        detail_grid.addWidget(self.detail_description, 2, 1)
        detail_layout.addLayout(detail_grid)
        detail_layout.addStretch(1)
        content_row.addWidget(detail_card, 1)
        root.addLayout(content_row, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Inventory Item Categories", callback=self.reload_categories)
        )
        self.btn_new.clicked.connect(
            make_guarded_slot(self, title="Inventory Item Categories", callback=self.create_category)
        )
        self.btn_edit.clicked.connect(
            make_guarded_slot(self, title="Inventory Item Categories", callback=self.edit_category)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Inventory Item Categories", callback=self.toggle_active)
        )
        self.search_edit.textChanged.connect(lambda _text: self.reload_categories())
        self.type_filter.currentIndexChanged.connect(lambda _index: self.reload_categories())
        self.usage_filter.currentIndexChanged.connect(lambda _index: self.reload_categories())
        self.active_filter.currentIndexChanged.connect(lambda _index: self.reload_categories())
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="inventory.manage")
        self._sync_actions()

    def reload_categories(self) -> None:
        selected_id = self._selected_category_id()
        try:
            self._rows = self._category_service.search_categories(
                search_text=self.search_text,
                active_only=self._selected_active_filter(),
                category_type=self._selected_type_filter(),
                equipment_only=self._selected_usage_flag("equipment"),
                project_usage_only=self._selected_usage_flag("project"),
                maintenance_usage_only=self._selected_usage_flag("maintenance"),
            )
            context_label = self._context_label()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Item Categories", str(exc))
            self._rows = []
            context_label = "-"
        except Exception as exc:
            QMessageBox.critical(self, "Inventory Item Categories", f"Failed to load categories: {exc}")
            self._rows = []
            context_label = "-"
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row, category in enumerate(self._rows):
            values = (
                category.category_code,
                category.name,
                category.category_type,
                "Yes" if category.is_equipment else "-",
                "Yes" if category.supports_project_usage else "-",
                "Yes" if category.supports_maintenance_usage else "-",
                "Yes" if category.is_active else "No",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.table.item(row, 0).setData(Qt.UserRole, category.id)
            if selected_id and category.id == selected_id:
                selected_row = row
        self._update_badges(context_label=context_label)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
            self._populate_details(self._selected_category())
        else:
            self.table.clearSelection()
            self._populate_details(None)

    def create_category(self) -> None:
        dialog = InventoryItemCategoryEditDialog(parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._category_service.create_category(
                    category_code=dialog.category_code,
                    name=dialog.name,
                    description=dialog.description,
                    category_type=dialog.category_type,
                    is_equipment=dialog.is_equipment,
                    supports_project_usage=dialog.supports_project_usage,
                    supports_maintenance_usage=dialog.supports_maintenance_usage,
                    is_active=dialog.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Inventory Item Categories", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Inventory Item Categories", f"Failed to create category: {exc}")
                return
            break
        self.reload_categories()

    def edit_category(self) -> None:
        category = self._selected_category()
        if category is None:
            QMessageBox.information(self, "Inventory Item Categories", "Please select a category.")
            return
        dialog = InventoryItemCategoryEditDialog(category=category, parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._category_service.update_category(
                    category.id,
                    category_code=dialog.category_code,
                    name=dialog.name,
                    description=dialog.description,
                    category_type=dialog.category_type,
                    is_equipment=dialog.is_equipment,
                    supports_project_usage=dialog.supports_project_usage,
                    supports_maintenance_usage=dialog.supports_maintenance_usage,
                    is_active=dialog.is_active,
                    expected_version=category.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Inventory Item Categories", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_categories()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Inventory Item Categories", f"Failed to update category: {exc}")
                return
            break
        self.reload_categories()

    def toggle_active(self) -> None:
        category = self._selected_category()
        if category is None:
            QMessageBox.information(self, "Inventory Item Categories", "Please select a category.")
            return
        try:
            self._category_service.update_category(
                category.id,
                is_active=not category.is_active,
                expected_version=category.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Inventory Item Categories", str(exc))
            if isinstance(exc, ConcurrencyError):
                self.reload_categories()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Inventory Item Categories", f"Failed to update category: {exc}")
            return
        self.reload_categories()

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip()

    def _selected_type_filter(self) -> str | None:
        return self.type_filter.currentData()

    def _selected_active_filter(self) -> bool | None:
        return self.active_filter.currentData()

    def _selected_usage_filter(self) -> str | None:
        return self.usage_filter.currentData()

    def _selected_usage_flag(self, usage_key: str) -> bool | None:
        selected = self._selected_usage_filter()
        if selected is None:
            return None
        return True if selected == usage_key else None

    def _selected_category_id(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return str(selected[0].data(Qt.UserRole) or "").strip() or None

    def _selected_category(self) -> InventoryItemCategory | None:
        selected_id = self._selected_category_id()
        if not selected_id:
            return None
        return next((row for row in self._rows if row.id == selected_id), None)

    def _sync_actions(self) -> None:
        has_selection = self._selected_category() is not None
        self.btn_edit.setEnabled(self._can_manage and has_selection)
        self.btn_toggle_active.setEnabled(self._can_manage and has_selection)

    def _update_badges(self, *, context_label: str) -> None:
        active_count = sum(1 for row in self._rows if row.is_active)
        equipment_count = sum(1 for row in self._rows if row.is_equipment)
        self.context_badge.setText(f"Context: {context_label}")
        self.count_badge.setText(f"{len(self._rows)} categories")
        self.active_badge.setText(f"{active_count} active")
        self.equipment_badge.setText(f"{equipment_count} equipment-ready")

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _on_categories_changed(self, _entity_id: str) -> None:
        self.reload_categories()

    def _on_selection_changed(self) -> None:
        self._populate_details(self._selected_category())
        self._sync_actions()

    def _populate_details(self, category: InventoryItemCategory | None) -> None:
        if category is None:
            self.detail_name.setText("Select a category")
            self.detail_status.setText("-")
            self.detail_type.setText("-")
            self.detail_usage.setText("-")
            self.detail_description.setText("-")
            return
        self.detail_name.setText(f"{category.category_code} - {category.name}")
        status_bits = ["ACTIVE" if category.is_active else "INACTIVE"]
        if category.is_equipment:
            status_bits.append("equipment-ready")
        self.detail_status.setText(" | ".join(status_bits))
        self.detail_type.setText(category.category_type)
        usage = []
        if category.supports_project_usage:
            usage.append("Projects")
        if category.supports_maintenance_usage:
            usage.append("Maintenance")
        self.detail_usage.setText(", ".join(usage) or "Inventory only")
        self.detail_description.setText(category.description or "-")


__all__ = ["InventoryItemCategoriesTab"]
