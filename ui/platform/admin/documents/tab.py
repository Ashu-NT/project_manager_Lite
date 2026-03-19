from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.documents import Document, DocumentLink, DocumentService
from core.platform.notifications.domain_events import domain_events
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.documents.dialogs import DocumentEditDialog, DocumentLinkEditDialog
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
        self._rows: list[Document] = []
        self._link_rows: list[DocumentLink] = []
        self._setup_ui()
        self.reload_documents()
        domain_events.documents_changed.connect(self._on_documents_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("documentAdminHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#documentAdminHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("DOCUMENT LIBRARY")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Documents")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel(
            "Manage shared enterprise document records and link them to module-owned business entities without duplicating document metadata."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.document_context_badge = QLabel("Context: -")
        self.document_context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.document_count_badge = QLabel("0 documents")
        self.document_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.document_active_badge = QLabel("0 active")
        self.document_active_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_documents else "Read Only"
        self.document_access_badge = QLabel(access_label)
        self.document_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.document_context_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.document_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.document_active_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.document_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("documentAdminControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#documentAdminControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_document = QPushButton("New Document")
        self.btn_edit_document = QPushButton("Edit Document")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_add_link = QPushButton("Add Link")
        self.btn_remove_link = QPushButton("Remove Link")
        for btn in (
            self.btn_refresh,
            self.btn_new_document,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new_document.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit_document.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_add_link.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_remove_link.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar.addWidget(self.btn_new_document)
        toolbar.addWidget(self.btn_edit_document)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addWidget(self.btn_add_link)
        toolbar.addWidget(self.btn_remove_link)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Code", "Title", "Type", "Revision", "Active"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        doc_header = self.table.horizontalHeader()
        doc_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        doc_header.setSectionResizeMode(1, QHeaderView.Stretch)
        doc_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        doc_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        doc_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        links_title = QLabel("Document Links")
        links_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(links_title)

        self.links_table = QTableWidget(0, 4)
        self.links_table.setHorizontalHeaderLabels(["Module", "Entity Type", "Entity Id", "Role"])
        style_table(self.links_table)
        self.links_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.links_table.setSelectionMode(QTableWidget.SingleSelection)
        self.links_table.setEditTriggers(QTableWidget.NoEditTriggers)
        link_header = self.links_table.horizontalHeader()
        link_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        link_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        link_header.setSectionResizeMode(2, QHeaderView.Stretch)
        link_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.links_table, 1)

        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.reload_documents))
        self.btn_new_document.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.create_document)
        )
        self.btn_edit_document.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.edit_document)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.toggle_active)
        )
        self.btn_add_link.clicked.connect(make_guarded_slot(self, title="Documents", callback=self.add_link))
        self.btn_remove_link.clicked.connect(
            make_guarded_slot(self, title="Documents", callback=self.remove_link)
        )
        self.table.itemSelectionChanged.connect(self._on_document_selection_changed)
        self.links_table.itemSelectionChanged.connect(self._sync_actions)
        for button in (
            self.btn_new_document,
            self.btn_edit_document,
            self.btn_toggle_active,
            self.btn_add_link,
            self.btn_remove_link,
        ):
            apply_permission_hint(button, allowed=self._can_manage_documents, missing_permission="settings.manage")
        self._sync_actions()

    def reload_documents(self) -> None:
        selected_id = self._selected_document_id()
        try:
            context = self._document_service.get_context_organization()
            self._rows = self._document_service.list_documents()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Documents", str(exc))
            context_label = "-"
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Documents", f"Failed to load documents: {exc}")
            context_label = "-"
            self._rows = []
        else:
            context_label = context.display_name
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row, document in enumerate(self._rows):
            values = (
                document.document_code,
                document.title,
                document.document_type.value.replace("_", " ").title(),
                document.revision or "-",
                "Yes" if document.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, document.id)
            if selected_id and document.id == selected_id:
                selected_row = row
        self._update_header_badges(self._rows, context_label=context_label)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
            self._link_rows = []
            self.links_table.setRowCount(0)
        if self._selected_document() is not None:
            self._reload_links_for_selected_document()
        self._sync_actions()

    def create_document(self) -> None:
        dlg = DocumentEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.create_document(
                    document_code=dlg.document_code,
                    title=dlg.title,
                    document_type=dlg.document_type,
                    storage_kind=dlg.storage_kind,
                    storage_uri=dlg.storage_uri,
                    file_name=dlg.file_name,
                    revision=dlg.revision,
                    source_system=dlg.source_system,
                    confidentiality_level=dlg.confidentiality_level,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
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
        dlg = DocumentEditDialog(parent=self, document=document)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.update_document(
                    document.id,
                    document_code=dlg.document_code,
                    title=dlg.title,
                    document_type=dlg.document_type,
                    storage_kind=dlg.storage_kind,
                    storage_uri=dlg.storage_uri,
                    file_name=dlg.file_name,
                    revision=dlg.revision,
                    source_system=dlg.source_system,
                    confidentiality_level=dlg.confidentiality_level,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
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
        dlg = DocumentLinkEditDialog(parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.add_link(
                    document_id=document.id,
                    module_code=dlg.module_code,
                    entity_type=dlg.entity_type,
                    entity_id=dlg.entity_id,
                    link_role=dlg.link_role,
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
        link = self._selected_link()
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

    def _reload_links_for_selected_document(self) -> None:
        document = self._selected_document()
        if document is None:
            self._link_rows = []
            self.links_table.setRowCount(0)
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
        self.links_table.setRowCount(len(self._link_rows))
        for row, link in enumerate(self._link_rows):
            values = (link.module_code, link.entity_type, link.entity_id, link.link_role or "-")
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.links_table.setItem(row, col, item)
            self.links_table.item(row, 0).setData(Qt.UserRole, link.id)
        self.links_table.clearSelection()
        self._sync_actions()

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

    def _selected_link(self) -> DocumentLink | None:
        row = self.links_table.currentRow()
        if row < 0:
            return None
        item = self.links_table.item(row, 0)
        if item is None:
            return None
        link_id = item.data(Qt.UserRole)
        for link in self._link_rows:
            if link.id == link_id:
                return link
        return None

    def _update_header_badges(self, rows: list[Document], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.document_context_badge.setText(f"Context: {context_label}")
        self.document_count_badge.setText(f"{len(rows)} documents")
        self.document_active_badge.setText(f"{active_count} active")

    def _on_document_selection_changed(self) -> None:
        self._reload_links_for_selected_document()

    def _on_documents_changed(self, _document_id: str) -> None:
        self.reload_documents()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_documents()

    def _sync_actions(self) -> None:
        has_document = self._selected_document() is not None
        has_link = self._selected_link() is not None
        self.btn_new_document.setEnabled(self._can_manage_documents)
        self.btn_edit_document.setEnabled(self._can_manage_documents and has_document)
        self.btn_toggle_active.setEnabled(self._can_manage_documents and has_document)
        self.btn_add_link.setEnabled(self._can_manage_documents and has_document)
        self.btn_remove_link.setEnabled(self._can_manage_documents and has_link)


__all__ = ["DocumentAdminTab"]
