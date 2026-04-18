from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryReportingService,
    InventoryService,
)
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.shared.header_support import (
    build_inventory_header_badge_widget,
    configure_inventory_header_layout,
)
from ui.modules.inventory_procurement.shared.reference_support import (
    build_party_lookup,
    build_site_lookup,
    format_party_label,
    format_site_label,
)
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class InventoryReportsTab(QWidget):
    def __init__(
        self,
        *,
        reporting_service: InventoryReportingService,
        reference_service: InventoryReferenceService,
        inventory_service: InventoryService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._reporting_service = reporting_service
        self._reference_service = reference_service
        self._inventory_service = inventory_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_export = has_permission(self._user_session, "report.export")
        self._site_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._all_storerooms: list[object] = []
        self._setup_ui()
        self.reload_filters()
        for signal in (
            domain_events.sites_changed,
            domain_events.parties_changed,
            domain_events.inventory_storerooms_changed,
            domain_events.organizations_changed,
        ):
            signal.connect(self._on_reference_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_SM)
        root.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)

        header = QWidget()
        self.report_header_card = header
        header.setObjectName("inventoryReportsHeaderCard")
        header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        header.setStyleSheet(
            f"""
            QWidget#inventoryReportsHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        intro = QVBoxLayout()
        configure_inventory_header_layout(header_layout=header_layout, intro_layout=intro)
        eyebrow = QLabel("REPORTING")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Inventory Reports")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Export stock status and procurement overview packages with site, storeroom, and supplier filters."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)

        self.context_badge = QLabel("Context: -")
        self.context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.package_badge = QLabel("2 report packs")
        self.package_badge.setStyleSheet(dashboard_meta_chip_style())
        self.access_badge = QLabel("Export Disabled")
        self.access_badge.setStyleSheet(dashboard_meta_chip_style())
        badge_widget = build_inventory_header_badge_widget(
            self.context_badge,
            self.package_badge,
            self.access_badge,
        )
        header_layout.addWidget(badge_widget, 0, Qt.AlignTop | Qt.AlignRight)
        root.addWidget(header)

        controls = QWidget()
        self.report_controls_card = controls
        controls.setObjectName("inventoryReportsControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"""
            QWidget#inventoryReportsControlSurface {{
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
        self.site_combo = QComboBox()
        self.site_combo.addItem("All sites", None)
        self.storeroom_combo = QComboBox()
        self.storeroom_combo.addItem("All storerooms", None)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("All suppliers", None)
        self.limit_combo = QComboBox()
        self.limit_combo.addItem("100 rows", 100)
        self.limit_combo.addItem("200 rows", 200)
        self.limit_combo.addItem("500 rows", 500)
        self.limit_combo.setCurrentIndex(1)
        filter_row.addWidget(QLabel("Site"))
        filter_row.addWidget(self.site_combo, 2)
        filter_row.addWidget(QLabel("Storeroom"))
        filter_row.addWidget(self.storeroom_combo, 2)
        filter_row.addWidget(QLabel("Supplier"))
        filter_row.addWidget(self.supplier_combo, 2)
        filter_row.addWidget(QLabel("Procurement limit"))
        filter_row.addWidget(self.limit_combo, 1)
        controls_layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_XS)
        self.btn_stock_csv = QPushButton("Stock CSV")
        self.btn_stock_excel = QPushButton("Stock Excel")
        self.btn_procurement_csv = QPushButton("Procurement CSV")
        self.btn_procurement_excel = QPushButton("Procurement Excel")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (
            self.btn_stock_csv,
            self.btn_stock_excel,
            self.btn_procurement_csv,
            self.btn_procurement_excel,
            self.btn_refresh,
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_stock_csv.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_stock_excel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_procurement_csv.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_procurement_excel.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_stock_csv)
        action_row.addWidget(self.btn_stock_excel)
        action_row.addWidget(self.btn_procurement_csv)
        action_row.addWidget(self.btn_procurement_excel)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(action_row)

        self.filter_summary = QLabel("")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        controls_layout.addWidget(self.filter_summary)
        root.addWidget(controls)
        root.addStretch(1)

        self.site_combo.currentIndexChanged.connect(self._on_site_filter_changed)
        self.supplier_combo.currentIndexChanged.connect(self._update_filter_summary)
        self.limit_combo.currentIndexChanged.connect(self._update_filter_summary)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Inventory Reports", callback=self.reload_filters))
        self.btn_stock_csv.clicked.connect(
            make_guarded_slot(self, title="Inventory Reports", callback=self.export_stock_status_csv)
        )
        self.btn_stock_excel.clicked.connect(
            make_guarded_slot(self, title="Inventory Reports", callback=self.export_stock_status_excel)
        )
        self.btn_procurement_csv.clicked.connect(
            make_guarded_slot(self, title="Inventory Reports", callback=self.export_procurement_overview_csv)
        )
        self.btn_procurement_excel.clicked.connect(
            make_guarded_slot(self, title="Inventory Reports", callback=self.export_procurement_overview_excel)
        )
        for button in (
            self.btn_stock_csv,
            self.btn_stock_excel,
            self.btn_procurement_csv,
            self.btn_procurement_excel,
        ):
            apply_permission_hint(button, allowed=self._can_export, missing_permission="report.export")
        self._sync_actions()

    def reload_filters(self) -> None:
        selected_site_id = self._selected_site_id()
        selected_storeroom_id = self._selected_storeroom_id()
        selected_supplier_id = self._selected_supplier_id()
        try:
            sites = self._reference_service.list_sites(active_only=None)
            suppliers = self._reference_service.list_business_parties(active_only=None)
            self._all_storerooms = list(self._inventory_service.list_storerooms(active_only=None))
            self._site_lookup = build_site_lookup(sites)
            self._party_lookup = build_party_lookup(suppliers)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Reports", str(exc))
            self._site_lookup = {}
            self._party_lookup = {}
            self._all_storerooms = []
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Reports", f"Failed to load report filters: {exc}")
            self._site_lookup = {}
            self._party_lookup = {}
            self._all_storerooms = []
        self._reload_site_filter(selected_site_id)
        self._reload_storeroom_filter(selected_storeroom_id)
        self._reload_supplier_filter(selected_supplier_id)
        self._update_badges()
        self._update_filter_summary()

    def export_stock_status_csv(self, output_path: str | Path | None = None):
        return self._export_stock("csv", Path(output_path) if output_path is not None else None)

    def export_stock_status_excel(self, output_path: str | Path | None = None):
        return self._export_stock("excel", Path(output_path) if output_path is not None else None)

    def export_procurement_overview_csv(self, output_path: str | Path | None = None):
        return self._export_procurement("csv", Path(output_path) if output_path is not None else None)

    def export_procurement_overview_excel(self, output_path: str | Path | None = None):
        return self._export_procurement("excel", Path(output_path) if output_path is not None else None)

    def _export_stock(self, format_name: str, output_path: Path | None):
        extension = "xlsx" if format_name == "excel" else "csv"
        file_filter = "Excel files (*.xlsx);;All files (*.*)" if format_name == "excel" else "CSV files (*.csv);;All files (*.*)"
        path = output_path or self._choose_export_path(
            title=f"Export stock status {format_name.upper()}",
            suggested_name=f"inventory-stock-status.{extension}",
            file_filter=file_filter,
        )
        if path is None:
            return None
        try:
            if format_name == "excel":
                artifact = self._reporting_service.generate_stock_status_excel(
                    path,
                    site_id=self._selected_site_id(),
                    storeroom_id=self._selected_storeroom_id(),
                )
            else:
                artifact = self._reporting_service.generate_stock_status_csv(
                    path,
                    site_id=self._selected_site_id(),
                    storeroom_id=self._selected_storeroom_id(),
                )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Reports", str(exc))
            return None
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Reports", f"Failed to export stock report: {exc}")
            return None
        QMessageBox.information(self, "Inventory Reports", f"Report exported to:\n{artifact.file_path}")
        return artifact.file_path

    def _export_procurement(self, format_name: str, output_path: Path | None):
        extension = "xlsx" if format_name == "excel" else "csv"
        file_filter = "Excel files (*.xlsx);;All files (*.*)" if format_name == "excel" else "CSV files (*.csv);;All files (*.*)"
        path = output_path or self._choose_export_path(
            title=f"Export procurement overview {format_name.upper()}",
            suggested_name=f"inventory-procurement-overview.{extension}",
            file_filter=file_filter,
        )
        if path is None:
            return None
        try:
            if format_name == "excel":
                artifact = self._reporting_service.generate_procurement_overview_excel(
                    path,
                    site_id=self._selected_site_id(),
                    storeroom_id=self._selected_storeroom_id(),
                    supplier_party_id=self._selected_supplier_id(),
                    limit=self._selected_limit(),
                )
            else:
                artifact = self._reporting_service.generate_procurement_overview_csv(
                    path,
                    site_id=self._selected_site_id(),
                    storeroom_id=self._selected_storeroom_id(),
                    supplier_party_id=self._selected_supplier_id(),
                    limit=self._selected_limit(),
                )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Inventory Reports", str(exc))
            return None
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Reports", f"Failed to export procurement report: {exc}")
            return None
        QMessageBox.information(self, "Inventory Reports", f"Report exported to:\n{artifact.file_path}")
        return artifact.file_path

    def _choose_export_path(self, *, title: str, suggested_name: str, file_filter: str) -> Path | None:
        file_path, _ = QFileDialog.getSaveFileName(self, title, suggested_name, file_filter)
        if not file_path:
            return None
        return Path(file_path)

    def _reload_site_filter(self, selected_site_id: str | None) -> None:
        self.site_combo.blockSignals(True)
        self.site_combo.clear()
        self.site_combo.addItem("All sites", None)
        for site_id in self._site_lookup.keys():
            self.site_combo.addItem(format_site_label(site_id, self._site_lookup), site_id)
        if selected_site_id:
            index = self.site_combo.findData(selected_site_id)
            if index >= 0:
                self.site_combo.setCurrentIndex(index)
        self.site_combo.blockSignals(False)

    def _reload_storeroom_filter(self, selected_storeroom_id: str | None) -> None:
        selected_site_id = self._selected_site_id()
        self.storeroom_combo.blockSignals(True)
        self.storeroom_combo.clear()
        self.storeroom_combo.addItem("All storerooms", None)
        for storeroom in self._filtered_storerooms(selected_site_id):
            label = f"{storeroom.storeroom_code} - {storeroom.name}"
            self.storeroom_combo.addItem(label, storeroom.id)
        if selected_storeroom_id:
            index = self.storeroom_combo.findData(selected_storeroom_id)
            if index >= 0:
                self.storeroom_combo.setCurrentIndex(index)
        self.storeroom_combo.blockSignals(False)

    def _reload_supplier_filter(self, selected_supplier_id: str | None) -> None:
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.clear()
        self.supplier_combo.addItem("All suppliers", None)
        for supplier_id in self._party_lookup.keys():
            self.supplier_combo.addItem(format_party_label(supplier_id, self._party_lookup), supplier_id)
        if selected_supplier_id:
            index = self.supplier_combo.findData(selected_supplier_id)
            if index >= 0:
                self.supplier_combo.setCurrentIndex(index)
        self.supplier_combo.blockSignals(False)

    def _filtered_storerooms(self, site_id: str | None) -> list[object]:
        if site_id is None:
            return list(self._all_storerooms)
        return [storeroom for storeroom in self._all_storerooms if getattr(storeroom, "site_id", None) == site_id]

    def _selected_site_id(self) -> str | None:
        value = self.site_combo.currentData()
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _selected_storeroom_id(self) -> str | None:
        value = self.storeroom_combo.currentData()
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _selected_supplier_id(self) -> str | None:
        value = self.supplier_combo.currentData()
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _selected_limit(self) -> int:
        value = self.limit_combo.currentData()
        try:
            return int(value)
        except (TypeError, ValueError):
            return 200

    def _on_site_filter_changed(self) -> None:
        selected_storeroom_id = self._selected_storeroom_id()
        self._reload_storeroom_filter(selected_storeroom_id)
        self._update_filter_summary()

    def _update_badges(self) -> None:
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.package_badge.setText("2 report packs")
        self.access_badge.setText("Export Enabled" if self._can_export else "Export Disabled")

    def _update_filter_summary(self) -> None:
        site_label = self.site_combo.currentText().strip() or "All sites"
        storeroom_label = self.storeroom_combo.currentText().strip() or "All storerooms"
        supplier_label = self.supplier_combo.currentText().strip() or "All suppliers"
        coverage = (
            f"Coverage: {len(self._site_lookup)} sites | "
            f"{len(self._filtered_storerooms(self._selected_site_id()))} storerooms | "
            f"{len(self._party_lookup)} suppliers"
        )
        self.filter_summary.setText(
            f"{coverage}. Filters: {site_label} | {storeroom_label} | {supplier_label} | limit {self._selected_limit()} rows"
        )
        self._update_badges()

    def _sync_actions(self) -> None:
        for button in (
            self.btn_stock_csv,
            self.btn_stock_excel,
            self.btn_procurement_csv,
            self.btn_procurement_excel,
        ):
            button.setEnabled(self._can_export)

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    def _on_reference_changed(self, _entity_id: str) -> None:
        self.reload_filters()


__all__ = ["InventoryReportsTab"]
