from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.platform import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import InventoryDataExchangeService
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from ui.modules.inventory_procurement.data_exchange.import_dialog import InventoryImportDialog
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG

_EXPORT_TYPES = {
    "Items": "items",
    "Storerooms": "storerooms",
    "Requisitions": "requisitions",
    "Purchase Orders": "purchase_orders",
    "Receipts": "receipts",
}

_EXPORT_DESCRIPTIONS = {
    "items": "Export the inventory item master including UOM, replenishment, and preferred-party fields.",
    "storerooms": "Export governed storeroom definitions with shared-site and manager-party references.",
    "requisitions": "Export raw requisition demand for downstream review or controlled handoff.",
    "purchase_orders": "Export purchase-order operational data including supplier, status, and sourcing fields.",
    "receipts": "Export receipt history and posted quantities for external reconciliation.",
}


class InventoryDataExchangeTab(QWidget):
    def __init__(
        self,
        *,
        data_exchange_service: InventoryDataExchangeService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data_exchange_service = data_exchange_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_import = has_permission(self._user_session, "import.manage")
        self._can_export = has_permission(self._user_session, "report.export")
        self._setup_ui()
        self._update_badges()
        self._sync_actions()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("inventoryDataExchangeHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#inventoryDataExchangeHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("DATA EXCHANGE")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Inventory Data Exchange")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Run governed inventory imports for master data and publish raw CSV feeds for inventory and procurement operations."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.import_badge = QLabel("2 import feeds")
        self.import_badge.setStyleSheet(dashboard_meta_chip_style())
        self.export_badge = QLabel("5 CSV feeds")
        self.export_badge.setStyleSheet(dashboard_meta_chip_style())
        self.access_badge = QLabel("No Runtime Access")
        self.access_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.import_badge,
            self.export_badge,
            self.access_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_import_card(), 1)
        content_row.addWidget(self._build_export_card(), 1)
        root.addLayout(content_row)

        coverage_card = QWidget()
        coverage_card.setObjectName("inventoryDataExchangeCoverageCard")
        coverage_card.setStyleSheet(
            f"""
            QWidget#inventoryDataExchangeCoverageCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        coverage_layout = QVBoxLayout(coverage_card)
        coverage_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        coverage_layout.setSpacing(CFG.SPACING_SM)
        coverage_title = QLabel("Current Coverage")
        coverage_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        coverage_layout.addWidget(coverage_title)
        for text in (
            "Imports: items and storerooms with preview, mapping, and validation.",
            "Raw CSV feeds: items, storerooms, requisitions, purchase orders, and receipts.",
            "Curated stock and procurement report packages are available from the Reports workspace.",
        ):
            label = QLabel(text)
            label.setStyleSheet(CFG.INFO_TEXT_STYLE)
            label.setWordWrap(True)
            coverage_layout.addWidget(label)
        root.addWidget(coverage_card)

        self.btn_open_import_wizard.clicked.connect(
            make_guarded_slot(self, title="Inventory Data Exchange", callback=self.open_import_wizard)
        )
        self.export_type_combo.currentIndexChanged.connect(self._sync_actions)
        self.btn_export_csv.clicked.connect(
            make_guarded_slot(self, title="Inventory Data Exchange", callback=self.export_selected_csv)
        )
        apply_permission_hint(
            self.btn_open_import_wizard,
            allowed=self._can_import,
            missing_permission="import.manage",
        )
        apply_permission_hint(
            self.btn_export_csv,
            allowed=self._can_export,
            missing_permission="report.export",
        )

    def _build_import_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("inventoryDataExchangeImportCard")
        card.setStyleSheet(
            f"""
            QWidget#inventoryDataExchangeImportCard {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)
        title = QLabel("Governed Imports")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        subtitle = QLabel(
            "Use the wizard to preview rows, map incoming columns, and import only valid item or storeroom records."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        self.btn_open_import_wizard = QPushButton("Open Import Wizard")
        self.btn_open_import_wizard.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_open_import_wizard.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_open_import_wizard.setStyleSheet(dashboard_action_button_style("primary"))
        supported = QLabel("Supported now: Items, Storerooms")
        supported.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        supported.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.btn_open_import_wizard, 0, Qt.AlignLeft)
        layout.addWidget(supported)
        layout.addStretch(1)
        return card

    def _build_export_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("inventoryDataExchangeExportCard")
        card.setStyleSheet(
            f"""
            QWidget#inventoryDataExchangeExportCard {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)
        title = QLabel("Raw CSV Feeds")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        subtitle = QLabel(
            "Export the operational record sets directly when another team needs raw module data instead of a curated report."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        self.export_type_combo = QComboBox()
        for label, value in _EXPORT_TYPES.items():
            self.export_type_combo.addItem(label, userData=value)
        self.active_only_check = QCheckBox("Active only")
        self.active_only_check.setChecked(True)
        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_export_csv.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_export_csv.setStyleSheet(dashboard_action_button_style("secondary"))
        row.addWidget(self.export_type_combo, 1)
        row.addWidget(self.active_only_check)
        row.addWidget(self.btn_export_csv)
        layout.addLayout(row)

        self.export_description = QLabel("")
        self.export_description.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.export_description.setWordWrap(True)
        layout.addWidget(self.export_description)
        layout.addStretch(1)
        return card

    def open_import_wizard(self) -> None:
        dialog = InventoryImportDialog(self, data_exchange_service=self._data_exchange_service)
        dialog.exec()

    def export_selected_csv(self, output_path: str | Path | None = None):
        entity_type = self._selected_export_type()
        path = Path(output_path) if output_path is not None else self._choose_export_path(entity_type)
        if path is None:
            return None
        kwargs: dict[str, object] = {}
        if entity_type in {"items", "storerooms"}:
            kwargs["active_only"] = self.active_only_check.isChecked()
        try:
            artifact = self._data_exchange_service.export_csv(entity_type, path, **kwargs)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Data Exchange", str(exc))
            return None
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Data Exchange", f"Failed to export CSV: {exc}")
            return None
        QMessageBox.information(
            self,
            "Inventory Data Exchange",
            f"CSV exported to:\n{artifact.file_path}",
        )
        return artifact.file_path

    def _choose_export_path(self, entity_type: str) -> Path | None:
        suggested_name = self._suggested_export_name(entity_type)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export inventory CSV",
            suggested_name,
            "CSV files (*.csv);;All files (*.*)",
        )
        if not file_path:
            return None
        return Path(file_path)

    def _selected_export_type(self) -> str:
        return str(self.export_type_combo.currentData() or "items")

    def _sync_actions(self) -> None:
        entity_type = self._selected_export_type()
        allow_active_only = entity_type in {"items", "storerooms"}
        self.active_only_check.setEnabled(allow_active_only)
        if not allow_active_only:
            self.active_only_check.setChecked(False)
        self.btn_open_import_wizard.setEnabled(self._can_import)
        self.btn_export_csv.setEnabled(self._can_export)
        self.export_description.setText(_EXPORT_DESCRIPTIONS.get(entity_type, ""))
        self._update_badges()

    def _update_badges(self) -> None:
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.access_badge.setText(self._access_label())

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _access_label(self) -> str:
        if self._can_import and self._can_export:
            return "Import & Export Enabled"
        if self._can_import:
            return "Import Enabled"
        if self._can_export:
            return "Export Enabled"
        return "No Runtime Access"

    @staticmethod
    def _suggested_export_name(entity_type: str) -> str:
        safe_entity = entity_type.replace("_", "-")
        return f"inventory-{safe_entity}.csv"


__all__ = ["InventoryDataExchangeTab"]
