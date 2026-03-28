from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.documents import Document, DocumentLink, DocumentService, DocumentType
from core.platform.notifications.domain_events import domain_events
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.documents.dialogs import DocumentEditDialog, DocumentLinkEditDialog
from ui.platform.admin.documents.preview import build_document_preview_state
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.admin.documents.viewer_dialogs import DocumentLinksDialog, DocumentPreviewDialog
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DocumentAdminTab(QWidget):
    def __init__(
        self,
        document_service: DocumentService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._document_service = document_service
        self._user_session = user_session
        self._can_manage_documents = has_permission(self._user_session, "settings.manage")
        self._context_label = "-"
        self._all_rows: list[Document] = []
        self._rows: list[Document] = []
        self._link_rows: list[DocumentLink] = []
        self._detail_labels: dict[str, QLabel] = {}
        self._setup_ui()
        self.reload_documents()
        domain_events.documents_changed.connect(self._on_documents_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        build_admin_header(
            self,
            root,
            object_name="documentAdminHeaderCard",
            eyebrow_text="DOCUMENT LIBRARY",
            title_text="Documents",
            subtitle_text="Browse enterprise documents with preview, metadata, and cross-module links for project, maintenance, QHSE, HR, and inventory workflows.",
            badge_specs=(
                ("document_context_badge", "Context: -", "accent"),
                ("document_count_badge", "0 documents", "meta"),
                ("document_active_badge", "0 active", "meta"),
                ("document_access_badge", "Manage Enabled" if self._can_manage_documents else "Read Only", "meta"),
            ),
        )

        controls = self._make_card("documentAdminControlSurface", alt=True)
        controls_layout = QVBoxLayout(controls)
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_document = QPushButton("New Document")
        self.btn_edit_document = QPushButton("Edit Document")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_add_link = QPushButton("Add Link")
        self.btn_remove_link = QPushButton("Remove Link")
        for button in (
            self.btn_refresh,
            self.btn_new_document,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_new_document.setStyleSheet(dashboard_action_button_style("primary"))
        for button in (
            self.btn_refresh,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            button.setStyleSheet(dashboard_action_button_style("secondary"))
        for button in (
            self.btn_new_document,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        helper = QLabel(
            "Platform documents stay shared. Modules link them to tasks, equipment, systems, inspections, employees, and reports without duplicating metadata."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        controls_layout.addWidget(helper)
        root.addWidget(controls)

        self._build_content(root)

    def _build_content(self, root: QVBoxLayout) -> None:
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_library_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([860, 620])

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.reload_documents))
        self.btn_new_document.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.create_document))
        self.btn_edit_document.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.edit_document))
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.toggle_active)
        )
        self.btn_add_link.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.add_link))
        self.btn_remove_link.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.remove_link))
        self.btn_preview_document.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.show_preview_dialog)
        )
        self.btn_view_links.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.show_links_dialog)
        )
        self.search_edit.textChanged.connect(self._apply_document_filters)
        self.type_filter_combo.currentIndexChanged.connect(self._apply_document_filters)
        self.active_filter_combo.currentIndexChanged.connect(self._apply_document_filters)
        self.table.itemSelectionChanged.connect(self._on_document_selection_changed)
        for button in (
            self.btn_new_document,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            apply_permission_hint(button, allowed=self._can_manage_documents, missing_permission="settings.manage")
        self._sync_actions()

    def _build_library_panel(self) -> QWidget:
        panel = self._make_card("documentLibraryPanel", alt=False)
        layout = QVBoxLayout(panel)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, title, file, source, or notes...")
        self.search_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.type_filter_combo.addItem("All types", userData=None)
        for document_type in DocumentType:
            self.type_filter_combo.addItem(document_type.value.replace("_", " ").title(), userData=document_type)
        self.active_filter_combo = QComboBox()
        self.active_filter_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.active_filter_combo.addItem("All statuses", userData=None)
        self.active_filter_combo.addItem("Active only", userData=True)
        self.active_filter_combo.addItem("Inactive only", userData=False)
        filters = QHBoxLayout()
        filters.addWidget(self.search_edit, 2)
        filters.addWidget(self.type_filter_combo, 1)
        filters.addWidget(self.active_filter_combo, 1)
        layout.addLayout(filters)
        self.filter_summary_label = QLabel("Library filter: showing all documents.")
        self.filter_summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary_label.setWordWrap(True)
        layout.addWidget(self.filter_summary_label)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Code", "Title", "Type", "File", "Revision", "Active"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)
        return panel

    def _build_detail_panel(self) -> QWidget:
        outer = self._make_card("documentDetailPanel", alt=False)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer_layout.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)

        summary = self._make_card("documentSelectionCard", alt=True)
        summary_layout = QVBoxLayout(summary)
        self.selected_document_title = QLabel("Select a document")
        self.selected_document_title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        self.selected_document_summary = QLabel("Document metadata, preview state, and linked records will appear here.")
        self.selected_document_summary.setWordWrap(True)
        self.selected_document_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.document_type_badge = QLabel("Type: -")
        self.document_storage_badge = QLabel("Storage: -")
        self.document_preview_badge = QLabel("Preview: -")
        self.document_link_badge = QLabel("0 links")
        badge_row = QHBoxLayout()
        for badge in (
            self.document_type_badge,
            self.document_storage_badge,
            self.document_preview_badge,
            self.document_link_badge,
        ):
            badge.setStyleSheet(dashboard_meta_chip_style())
            badge_row.addWidget(badge)
        badge_row.addStretch(1)
        summary_layout.addWidget(self.selected_document_title)
        summary_layout.addWidget(self.selected_document_summary)
        summary_layout.addLayout(badge_row)
        action_row = QHBoxLayout()
        self.btn_preview_document = QPushButton("Preview File")
        self.btn_view_links = QPushButton("View Linked Records")
        for button in (self.btn_preview_document, self.btn_view_links):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        action_row.addStretch(1)
        summary_layout.addLayout(action_row)
        layout.addWidget(summary)

        metadata_card = self._make_card("documentMetadataCard", alt=True)
        metadata_layout = QVBoxLayout(metadata_card)
        metadata_title = QLabel("Metadata")
        metadata_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        metadata_layout.addWidget(metadata_title)
        form = QFormLayout()
        for key, label in (
            ("code", "Code:"),
            ("file_name", "File name:"),
            ("mime_type", "Mime type:"),
            ("revision", "Revision:"),
            ("source", "Source system:"),
            ("confidentiality", "Confidentiality:"),
            ("uploaded", "Uploaded:"),
            ("uploaded_by", "Uploaded by:"),
            ("effective", "Effective date:"),
            ("review", "Review date:"),
            ("storage_uri", "Storage URI:"),
        ):
            self._detail_labels[key] = self._make_value_label()
            form.addRow(label, self._detail_labels[key])
        metadata_layout.addLayout(form)
        notes_title = QLabel("Notes")
        notes_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        metadata_layout.addWidget(notes_title)
        self.detail_notes_value = QPlainTextEdit()
        self.detail_notes_value.setReadOnly(True)
        self.detail_notes_value.setMinimumHeight(90)
        metadata_layout.addWidget(self.detail_notes_value)
        layout.addWidget(metadata_card)
        layout.addStretch(1)
        return outer

    def reload_documents(self) -> None:
        selected_id = self._selected_document_id()
        try:
            context = self._document_service.get_context_organization()
            self._all_rows = self._document_service.list_documents()
            self._context_label = context.display_name
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Documents", str(exc))
            self._context_label = "-"
            self._all_rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Documents", f"Failed to load documents: {exc}")
            self._context_label = "-"
            self._all_rows = []
        self._apply_document_filters(selected_id=selected_id)

    def create_document(self) -> None:
        dialog = DocumentEditDialog(parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.create_document(
                    document_code=dialog.document_code,
                    title=dialog.title,
                    document_type=dialog.document_type,
                    storage_kind=dialog.storage_kind,
                    storage_uri=dialog.storage_uri,
                    file_name=dialog.file_name,
                    revision=dialog.revision,
                    source_system=dialog.source_system,
                    confidentiality_level=dialog.confidentiality_level,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Documents", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Documents", f"Failed to create document: {exc}")
                return
            break
        self.reload_documents()

    def edit_document(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document.")
            return
        dialog = DocumentEditDialog(parent=self, document=document)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.update_document(
                    document.id,
                    document_code=dialog.document_code,
                    title=dialog.title,
                    document_type=dialog.document_type,
                    storage_kind=dialog.storage_kind,
                    storage_uri=dialog.storage_uri,
                    file_name=dialog.file_name,
                    revision=dialog.revision,
                    source_system=dialog.source_system,
                    confidentiality_level=dialog.confidentiality_level,
                    notes=dialog.notes,
                    is_active=dialog.is_active,
                    expected_version=document.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Documents", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_documents()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Documents", f"Failed to update document: {exc}")
                return
            break
        self.reload_documents()

    def toggle_active(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document.")
            return
        try:
            self._document_service.update_document(
                document.id,
                is_active=not document.is_active,
                expected_version=document.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Documents", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Documents", f"Failed to update document: {exc}")
            return
        self.reload_documents()

    def add_link(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document first.")
            return
        dialog = DocumentLinkEditDialog(parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.add_link(
                    document_id=document.id,
                    module_code=dialog.module_code,
                    entity_type=dialog.entity_type,
                    entity_id=dialog.entity_id,
                    link_role=dialog.link_role,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Documents", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Documents", f"Failed to link document: {exc}")
                return
            break
        self._reload_links_for_selected_document()

    def remove_link(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document first.")
            return
        if not self._link_rows:
            QMessageBox.information(self, "Documents", "The selected document has no linked records.")
            return
        dialog = DocumentLinksDialog(document=document, links=self._link_rows, selection_mode=True, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        link = dialog.selected_link
        if link is None:
            QMessageBox.information(self, "Documents", "Please select a document link.")
            return
        try:
            self._document_service.remove_link(link.id)
        except (ValidationError, NotFoundError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Documents", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Documents", f"Failed to remove document link: {exc}")
            return
        self._reload_links_for_selected_document()

    def _apply_document_filters(self, *_args, selected_id: str | None = None) -> None:
        selected_id = selected_id or self._selected_document_id()
        search = self.search_edit.text().strip().lower()
        selected_type = self.type_filter_combo.currentData()
        selected_active = self.active_filter_combo.currentData()
        self._rows = []
        for document in self._all_rows:
            if search:
                haystack = " ".join(
                    [
                        document.document_code,
                        document.title,
                        document.file_name,
                        document.storage_uri,
                        document.source_system,
                        document.notes,
                    ]
                ).lower()
                if search not in haystack:
                    continue
            if selected_type is not None and document.document_type != selected_type:
                continue
            if selected_active is not None and document.is_active != bool(selected_active):
                continue
            self._rows.append(document)

        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row, document in enumerate(self._rows):
            values = (
                document.document_code,
                document.title,
                document.document_type.value.replace("_", " ").title(),
                document.file_name or "-",
                document.revision or "-",
                "Yes" if document.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 5:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, document.id)
            if selected_id and document.id == selected_id:
                selected_row = row

        self._update_header_badges()
        self.filter_summary_label.setText(
            f"Library filter: search={search or 'none'} | type={self.type_filter_combo.currentText()} | status={self.active_filter_combo.currentText()}."
        )
        if selected_row >= 0:
            self.table.selectRow(selected_row)
            self._reload_links_for_selected_document()
        elif self._rows:
            self.table.selectRow(0)
            self._reload_links_for_selected_document()
        else:
            self.table.clearSelection()
            self._link_rows = []
            self._render_detail(None)
        self._sync_actions()

    def _update_header_badges(self) -> None:
        total = len(self._all_rows)
        shown = len(self._rows)
        active = sum(1 for row in self._all_rows if row.is_active)
        self.document_context_badge.setText(f"Context: {self._context_label}")
        self.document_count_badge.setText(f"{shown} shown / {total} documents" if shown != total else f"{total} documents")
        self.document_active_badge.setText(f"{active} active")

    def _reload_links_for_selected_document(self) -> None:
        document = self._selected_document()
        if document is None:
            self._link_rows = []
            self._render_detail(None)
            self._sync_actions()
            return
        try:
            self._link_rows = self._document_service.list_links(document.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Documents", str(exc))
            self._link_rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Documents", f"Failed to load document links: {exc}")
            self._link_rows = []
        self._render_detail(document)
        self._sync_actions()

    def _render_detail(self, document: Document | None) -> None:
        if document is None:
            self.selected_document_title.setText("Select a document")
            self.selected_document_summary.setText("Document metadata, preview state, and linked records will appear here.")
            self.document_type_badge.setText("Type: -")
            self.document_storage_badge.setText("Storage: -")
            self.document_preview_badge.setText("Preview: -")
            self.document_link_badge.setText("0 links")
            self.btn_preview_document.setEnabled(False)
            self.btn_view_links.setEnabled(False)
            self.btn_view_links.setText("View Linked Records")
            for label in self._detail_labels.values():
                label.setText("-")
            self.detail_notes_value.setPlainText("")
            return
        preview_state = build_document_preview_state(document)
        self.selected_document_title.setText(document.title)
        self.selected_document_summary.setText(
            f"{document.document_code} | {document.document_type.value.replace('_', ' ').title()} | {'Active' if document.is_active else 'Inactive'} | {len(self._link_rows)} linked records"
        )
        self.document_type_badge.setText(f"Type: {document.document_type.value.replace('_', ' ').title()}")
        self.document_storage_badge.setText(f"Storage: {document.storage_kind.value.replace('_', ' ').title()}")
        self.document_preview_badge.setText(f"Preview: {preview_state.status_label}")
        self.document_link_badge.setText(f"{len(self._link_rows)} links")
        self.btn_preview_document.setEnabled(True)
        self.btn_view_links.setEnabled(True)
        self.btn_view_links.setText(f"View Linked Records ({len(self._link_rows)})")
        values = {
            "code": document.document_code or "-",
            "file_name": document.file_name or "-",
            "mime_type": document.mime_type or "-",
            "revision": document.revision or "-",
            "source": document.source_system or "-",
            "confidentiality": document.confidentiality_level or "-",
            "uploaded": self._format_datetime(document.uploaded_at),
            "uploaded_by": document.uploaded_by_user_id or "-",
            "effective": self._format_date(document.effective_date),
            "review": self._format_date(document.review_date),
            "storage_uri": document.storage_uri or "-",
        }
        for key, value in values.items():
            self._detail_labels[key].setText(value)
        self.detail_notes_value.setPlainText(document.notes or "")

    def _selected_document_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item is not None else None

    def _selected_document(self) -> Document | None:
        selected_id = self._selected_document_id()
        if not selected_id:
            return None
        for document in self._rows:
            if document.id == selected_id:
                return document
        return None

    def _on_document_selection_changed(self) -> None:
        self._reload_links_for_selected_document()

    def _on_documents_changed(self, _document_id: str) -> None:
        self.reload_documents()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_documents()

    def _sync_actions(self) -> None:
        has_document = self._selected_document() is not None
        self.btn_new_document.setEnabled(self._can_manage_documents)
        self.btn_edit_document.setEnabled(self._can_manage_documents and has_document)
        self.btn_toggle_active.setEnabled(self._can_manage_documents and has_document)
        self.btn_add_link.setEnabled(self._can_manage_documents and has_document)
        self.btn_remove_link.setEnabled(self._can_manage_documents and has_document and bool(self._link_rows))
        self.btn_preview_document.setEnabled(has_document)
        self.btn_view_links.setEnabled(has_document)

    def show_preview_dialog(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document.")
            return
        dialog = DocumentPreviewDialog(document=document, parent=self)
        dialog.exec()

    def show_links_dialog(self) -> None:
        document = self._selected_document()
        if document is None:
            QMessageBox.information(self, "Documents", "Please select a document.")
            return
        dialog = DocumentLinksDialog(document=document, links=self._link_rows, parent=self)
        dialog.exec()

    @staticmethod
    def _make_card(object_name: str, *, alt: bool) -> QWidget:
        widget = QWidget()
        widget.setObjectName(object_name)
        background = CFG.COLOR_BG_SURFACE_ALT if alt else CFG.COLOR_BG_SURFACE
        widget.setStyleSheet(
            f"QWidget#{object_name} {{ background-color: {background}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        return widget

    @staticmethod
    def _make_value_label() -> QLabel:
        label = QLabel("-")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(f"color: {CFG.COLOR_TEXT_PRIMARY};")
        return label

    @staticmethod
    def _format_date(value: date | None) -> str:
        return value.isoformat() if value is not None else "-"

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%d %H:%M") if value is not None else "-"


__all__ = ["DocumentAdminTab"]
