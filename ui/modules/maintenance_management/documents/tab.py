from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import MaintenanceDocumentService
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    format_timestamp,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.documents.preview import build_document_preview_state
from ui.platform.admin.documents.viewer_dialogs import DocumentLinksDialog, DocumentPreviewDialog
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


_ENTITY_TYPE_LABELS = {
    "location": "Location",
    "system": "System",
    "asset": "Asset",
    "work_request": "Work Request",
    "work_order": "Work Order",
}


class MaintenanceDocumentLinkDialog(QDialog):
    def __init__(
        self,
        *,
        document_service: MaintenanceDocumentService,
        site_service: SiteService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document_service = document_service
        self._site_service = site_service
        self.setWindowTitle("Link Maintenance Document")
        self.setModal(True)
        self.resize(620, 240)
        self._setup_ui()
        self._reload_sites()
        self._reload_documents()
        self._reload_entities()

    @property
    def site_id(self) -> str | None:
        return selected_combo_value(self.site_combo)

    @property
    def entity_type(self) -> str:
        return str(self.entity_type_combo.currentData() or "asset")

    @property
    def entity_id(self) -> str | None:
        return selected_combo_value(self.entity_combo)

    @property
    def document_id(self) -> str | None:
        return selected_combo_value(self.document_combo)

    @property
    def link_role(self) -> str:
        return self.link_role_edit.text().strip() or "reference"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.site_combo = QComboBox()
        self.entity_type_combo = QComboBox()
        for key, label in _ENTITY_TYPE_LABELS.items():
            self.entity_type_combo.addItem(label, key)
        self.entity_combo = QComboBox()
        self.document_combo = QComboBox()
        self.link_role_edit = QLineEdit("reference")
        form.addRow("Site", self.site_combo)
        form.addRow("Linked record", self.entity_type_combo)
        form.addRow("Entity", self.entity_combo)
        form.addRow("Document", self.document_combo)
        form.addRow("Role", self.link_role_edit)
        layout.addLayout(form)
        self.summary_label = QLabel("Choose a maintenance record and a shared document to link.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        layout.addWidget(self.summary_label)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_link = QPushButton("Link")
        self.btn_link.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_cancel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_cancel.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_link.setFixedHeight(CFG.BUTTON_HEIGHT)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_link)
        layout.addLayout(buttons)

        self.site_combo.currentIndexChanged.connect(self._reload_entities)
        self.entity_type_combo.currentIndexChanged.connect(self._reload_entities)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_link.clicked.connect(self._accept_if_valid)

    def _reload_sites(self) -> None:
        try:
            rows = self._site_service.list_sites(active_only=None)
        except Exception:  # noqa: BLE001
            rows = []
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{row.site_code} - {row.name}", row.id) for row in rows],
            selected_value=None,
        )

    def _reload_documents(self) -> None:
        try:
            rows = self._document_service.list_available_documents(active_only=True)
        except Exception:  # noqa: BLE001
            rows = []
        reset_combo_options(
            self.document_combo,
            placeholder="Select document",
            options=[(f"{row.document_code} - {row.title}", row.id) for row in rows],
            selected_value=None,
        )

    def _reload_entities(self) -> None:
        try:
            rows = self._document_service.list_entity_choices(
                entity_type=self.entity_type,
                site_id=self.site_id,
            )
        except Exception:  # noqa: BLE001
            rows = []
        reset_combo_options(
            self.entity_combo,
            placeholder="Select entity",
            options=rows,
            selected_value=None,
        )
        self.summary_label.setText(
            f"Linking a shared document to {_ENTITY_TYPE_LABELS.get(self.entity_type, self.entity_type)} records in {self.site_combo.currentText()}."
        )

    def _accept_if_valid(self) -> None:
        if not self.document_id:
            QMessageBox.information(self, "Maintenance Documents", "Please select a document.")
            return
        if not self.entity_id:
            QMessageBox.information(self, "Maintenance Documents", "Please select a maintenance record.")
            return
        self.accept()


class MaintenanceDocumentsTab(QWidget):
    def __init__(
        self,
        *,
        document_service: MaintenanceDocumentService,
        site_service: SiteService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document_service = document_service
        self._site_service = site_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage_documents = has_permission(self._user_session, "maintenance.manage")
        self._rows = []
        self._setup_ui()
        self.reload_data()
        domain_events.domain_changed.connect(self._on_domain_change)
        domain_events.documents_changed.connect(self._on_documents_changed)
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organization_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.context_badge = make_accent_badge("Context: -")
        self.doc_count_badge = make_meta_badge("0 linked docs")
        self.doc_access_badge = make_meta_badge("Manage Enabled" if self._can_manage_documents else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceDocumentsHeaderCard",
            eyebrow_text="DOCUMENT CONTROL",
            title_text="Documents",
            subtitle_text="Browse shared maintenance documents across assets, systems, requests, and work orders without duplicating the platform library.",
            badges=(self.context_badge, self.doc_count_badge, self.doc_access_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenanceDocumentsControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All records | Active docs")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        toolbar_row.addWidget(self.filter_summary, 1)
        self.btn_filters = make_filter_toggle_button(self)
        self.btn_link_document = QPushButton("Link Existing")
        self.btn_unlink_document = QPushButton("Unlink")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_link_document, self.btn_unlink_document, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar_row.addWidget(self.btn_filters)
        toolbar_row.addWidget(self.btn_link_document)
        toolbar_row.addWidget(self.btn_unlink_document)
        toolbar_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar_row)

        self.filter_panel = QWidget()
        filter_row = QGridLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setHorizontalSpacing(CFG.SPACING_MD)
        filter_row.setVerticalSpacing(CFG.SPACING_SM)
        self.site_combo = QComboBox()
        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItem("All records", None)
        for key, label in _ENTITY_TYPE_LABELS.items():
            self.entity_type_combo.addItem(label, key)
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active docs", True)
        self.active_combo.addItem("Inactive docs", False)
        self.active_combo.addItem("All statuses", None)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, title, linked record, structure, source, or role")
        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Record type"), 0, 2)
        filter_row.addWidget(self.entity_type_combo, 0, 3)
        filter_row.addWidget(QLabel("Status"), 1, 0)
        filter_row.addWidget(self.active_combo, 1, 1)
        filter_row.addWidget(QLabel("Search"), 1, 2)
        filter_row.addWidget(self.search_edit, 1, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Linked Docs", "-", "Visible in current scope", CFG.COLOR_ACCENT)
        self.asset_card = KpiCard("Asset Docs", "-", "Asset-linked records", CFG.COLOR_SUCCESS)
        self.work_order_card = KpiCard("Work Order Docs", "-", "Execution-linked records", CFG.COLOR_WARNING)
        self.request_card = KpiCard("Request Docs", "-", "Request-linked records", CFG.COLOR_ACCENT)
        for card in (self.total_card, self.asset_card, self.work_order_card, self.request_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_library_panel(), 3)
        content_row.addWidget(self._build_detail_panel(), 2)
        root.addLayout(content_row, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_link_document.clicked.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.link_document)
        )
        self.btn_unlink_document.clicked.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.unlink_document)
        )
        self.site_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.reload_data)
        )
        self.entity_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.reload_documents)
        )
        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.reload_documents)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.reload_documents)
        )
        self.document_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self._on_selection_changed)
        )
        self.btn_preview_document.clicked.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.show_preview_dialog)
        )
        self.btn_view_links.clicked.connect(
            make_guarded_slot(self, title="Maintenance Documents", callback=self.show_links_dialog)
        )
        for button in (self.btn_link_document, self.btn_unlink_document):
            apply_permission_hint(button, allowed=self._can_manage_documents, missing_permission="maintenance.manage")
        self._sync_actions()

    def _build_library_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceDocumentsLibrarySurface",
            alt=False,
        )
        title = QLabel("Document Links")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Shared documents linked into maintenance records and work execution.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.document_table = build_admin_table(
            headers=("Document", "Linked Record", "Site", "Role", "Type", "Structure"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.document_table)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenanceDocumentsDetailSurface",
            alt=False,
        )
        title = QLabel("Selected Document")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Metadata stays visible here while preview and linked-record browsing open in focused dialogs.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.detail_title = QLabel("No document selected")
        self.detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(self.detail_title)
        self.detail_summary = QLabel("Select a linked maintenance document to inspect its metadata and record context.")
        self.detail_summary.setWordWrap(True)
        self.detail_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(self.detail_summary)
        action_row = QHBoxLayout()
        self.btn_preview_document = QPushButton("Preview File")
        self.btn_view_links = QPushButton("View Linked Records")
        for button in (self.btn_preview_document, self.btn_view_links):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        metadata = QFormLayout()
        self.metadata_labels = {}
        for key, label in (
            ("code", "Code:"),
            ("linked_record", "Linked record:"),
            ("role", "Link role:"),
            ("type", "Document type:"),
            ("structure", "Structure:"),
            ("file_name", "File name:"),
            ("mime_type", "Mime type:"),
            ("version", "Version / revision:"),
            ("source", "Source system:"),
            ("uploaded", "Uploaded:"),
            ("site", "Site:"),
        ):
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value_label.setStyleSheet(f"color: {CFG.COLOR_TEXT_PRIMARY};")
            self.metadata_labels[key] = value_label
            metadata.addRow(label, value_label)
        layout.addLayout(metadata)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_link_id = self._selected_link_id()
        try:
            sites = self._site_service.list_sites(active_only=None)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Documents", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Documents", f"Failed to load document filters: {exc}")
            return
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{row.site_code} - {row.name}", row.id) for row in sites],
            selected_value=selected_site_id,
        )
        self.reload_documents(selected_link_id=selected_link_id)

    def reload_documents(self, *, selected_link_id: str | None = None) -> None:
        selected_link_id = selected_link_id or self._selected_link_id()
        try:
            self._rows = self._document_service.list_document_records(
                site_id=selected_combo_value(self.site_combo),
                entity_type=selected_combo_value(self.entity_type_combo),
                active_only=self.active_combo.currentData(),
                search_text=self.search_edit.text(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Maintenance Documents", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Documents", f"Failed to load maintenance documents: {exc}")
            return

        self.total_card.set_value(str(len(self._rows)))
        self.asset_card.set_value(str(sum(1 for row in self._rows if row.entity_type == "asset")))
        self.work_order_card.set_value(str(sum(1 for row in self._rows if row.entity_type == "work_order")))
        self.request_card.set_value(str(sum(1 for row in self._rows if row.entity_type == "work_request")))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.doc_count_badge.setText(f"{len(self._rows)} linked docs")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.entity_type_combo.currentText()} | {self.active_combo.currentText()}"
            + (
                f" | Search: {self.search_edit.text().strip()}"
                if self.search_edit.text().strip()
                else ""
            )
        )
        self._populate_table(selected_link_id=selected_link_id)

    def _populate_table(self, *, selected_link_id: str | None) -> None:
        self.document_table.blockSignals(True)
        self.document_table.setRowCount(len(self._rows))
        selected_row = 0 if self._rows else -1
        for row_index, row in enumerate(self._rows):
            values = (
                f"{row.document.document_code} - {row.document.title}",
                f"{_ENTITY_TYPE_LABELS.get(row.entity_type, row.entity_type)}: {row.entity_label}",
                row.site_label or "-",
                row.link_role or "-",
                row.document.document_type.value.replace("_", " ").title(),
                row.structure.structure_code if row.structure is not None else "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.link_id)
                self.document_table.setItem(row_index, column, item)
            if selected_link_id and row.link_id == selected_link_id:
                selected_row = row_index
        self.document_table.blockSignals(False)
        if selected_row >= 0:
            self.document_table.selectRow(selected_row)
            self._render_detail(self._rows[selected_row])
            return
        self._render_detail(None)

    def link_document(self) -> None:
        dialog = MaintenanceDocumentLinkDialog(
            document_service=self._document_service,
            site_service=self._site_service,
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            link = self._document_service.link_existing_document(
                entity_type=dialog.entity_type,
                entity_id=dialog.entity_id or "",
                document_id=dialog.document_id or "",
                link_role=dialog.link_role,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Maintenance Documents", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Documents", f"Failed to link document: {exc}")
            return
        self.reload_documents(selected_link_id=link.id)

    def unlink_document(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Maintenance Documents", "Please select a linked document.")
            return
        try:
            self._document_service.unlink_document_link(row.link_id)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Maintenance Documents", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Documents", f"Failed to unlink document: {exc}")
            return
        self.reload_documents()

    def show_preview_dialog(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Maintenance Documents", "Please select a linked document.")
            return
        DocumentPreviewDialog(document=row.document, parent=self).exec()

    def show_links_dialog(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Maintenance Documents", "Please select a linked document.")
            return
        try:
            links = self._document_service.list_links_for_document(row.document.id)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Maintenance Documents", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Maintenance Documents", f"Failed to load document links: {exc}")
            return
        DocumentLinksDialog(document=row.document, links=links, parent=self).exec()

    def _render_detail(self, row) -> None:
        if row is None:
            self.detail_title.setText("No document selected")
            self.detail_summary.setText("Select a linked maintenance document to inspect its metadata and record context.")
            for label in self.metadata_labels.values():
                label.setText("-")
            self.btn_preview_document.setEnabled(False)
            self.btn_view_links.setEnabled(False)
            self._sync_actions()
            return
        preview_state = build_document_preview_state(row.document)
        self.detail_title.setText(row.document.title)
        self.detail_summary.setText(
            f"{row.document.document_code} linked to {_ENTITY_TYPE_LABELS.get(row.entity_type, row.entity_type)} {row.entity_label}. Preview state: {preview_state.status_label}."
        )
        self.metadata_labels["code"].setText(row.document.document_code or "-")
        self.metadata_labels["linked_record"].setText(f"{_ENTITY_TYPE_LABELS.get(row.entity_type, row.entity_type)}: {row.entity_label}")
        self.metadata_labels["role"].setText(row.link_role or "-")
        self.metadata_labels["type"].setText(row.document.document_type.value.replace("_", " ").title())
        self.metadata_labels["structure"].setText(
            f"{row.structure.structure_code} - {row.structure.name}" if row.structure is not None else "-"
        )
        self.metadata_labels["file_name"].setText(row.document.file_name or "-")
        self.metadata_labels["mime_type"].setText(row.document.mime_type or "-")
        self.metadata_labels["version"].setText(row.document.business_version_label or "-")
        self.metadata_labels["source"].setText(row.document.source_system or "-")
        self.metadata_labels["uploaded"].setText(format_timestamp(row.document.uploaded_at))
        self.metadata_labels["site"].setText(row.site_label or "-")
        self.btn_preview_document.setEnabled(True)
        self.btn_view_links.setEnabled(True)
        self._sync_actions()

    def _selected_link_id(self) -> str | None:
        row = self.document_table.currentRow()
        if row < 0:
            return None
        item = self.document_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_row(self):
        selected_link_id = self._selected_link_id()
        if not selected_link_id:
            return None
        for row in self._rows:
            if row.link_id == selected_link_id:
                return row
        return None

    def _on_selection_changed(self) -> None:
        self._render_detail(self._selected_row())

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _sync_actions(self) -> None:
        has_row = self._selected_row() is not None
        self.btn_link_document.setEnabled(self._can_manage_documents)
        self.btn_unlink_document.setEnabled(self._can_manage_documents and has_row)
        self.btn_preview_document.setEnabled(has_row)
        self.btn_view_links.setEnabled(has_row)

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") == "maintenance_management":
            self.reload_documents()

    def _on_documents_changed(self, _document_id: str) -> None:
        self.reload_documents()

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_documents()

    def _on_organization_changed(self, _organization_id: str) -> None:
        self.reload_data()

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceDocumentsTab"]
