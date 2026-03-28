from __future__ import annotations

from core.platform.documents.domain import Document, DocumentStorageKind, DocumentType
from ui.platform.admin.documents.dialogs import DocumentEditDialog
from ui.platform.admin.documents.preview import build_document_preview_state
from ui.platform.admin.documents.tab import DocumentAdminTab


def test_document_admin_tab_filters_documents_and_shows_selected_metadata(qapp, services, tmp_path):
    pdf_path = tmp_path / "pump-manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    structure = services["document_service"].create_document_structure(
        structure_code="ASSET_MANUALS",
        name="Asset Manuals",
        object_scope="ASSET",
        default_document_type="MANUAL",
    )

    document = services["document_service"].create_document(
        document_code="DOC-PUMP",
        title="Pump Manual",
        document_type="MANUAL",
        document_structure_id=structure.id,
        storage_kind="FILE_PATH",
        storage_uri=str(pdf_path),
        confidentiality_level="INTERNAL",
        business_version_label="R2",
        notes="Maintenance and project startup reference.",
    )
    services["document_service"].add_link(
        document_id=document.id,
        module_code="maintenance_management",
        entity_type="asset",
        entity_id="asset-001",
        link_role="reference",
    )
    services["document_service"].create_document(
        document_code="DOC-CERT",
        title="Operator Certificate",
        document_type="CERTIFICATE",
        storage_kind="REFERENCE",
        storage_uri="vault://hr/cert-001",
        is_active=False,
    )

    tab = DocumentAdminTab(
        document_service=services["document_service"],
        user_session=services["user_session"],
    )
    qapp.processEvents()

    assert tab.table.rowCount() == 2

    tab.search_edit.setText("pump")
    qapp.processEvents()

    assert tab.table.rowCount() == 1
    assert tab.selected_document_title.text() == "Pump Manual"
    assert tab.document_link_badge.text() == "1 links"
    assert tab.document_structure_badge.text() == "1 structures"
    assert tab._detail_labels["structure"].text() == "ASSET_MANUALS - Asset Manuals"
    assert tab._detail_labels["mime_type"].text() == "application/pdf"
    assert tab.btn_preview_document.isEnabled() is True
    assert tab.btn_view_links.text() == "View Linked Records (1)"
    assert not hasattr(tab, "preview_panel")
    assert not hasattr(tab, "links_table")

    tab.search_edit.clear()
    tab.structure_filter_combo.setCurrentIndex(tab.structure_filter_combo.findData(structure.id))
    qapp.processEvents()

    assert tab.table.rowCount() == 1
    assert tab.selected_document_title.text() == "Pump Manual"

    tab.structure_filter_combo.setCurrentIndex(0)
    tab.active_filter_combo.setCurrentIndex(tab.active_filter_combo.findData(False))
    qapp.processEvents()

    assert tab.table.rowCount() == 1
    assert tab.selected_document_title.text() == "Operator Certificate"


def test_document_preview_state_marks_reference_documents_as_metadata_only():
    document = Document.create(
        organization_id="org-1",
        document_code="DOC-REF",
        title="Asset Register Link",
        document_type=DocumentType.GENERAL,
        storage_kind=DocumentStorageKind.REFERENCE,
        storage_uri="vault://assets/asset-register",
    )

    state = build_document_preview_state(document)

    assert state.status_label == "Metadata reference"
    assert state.can_open is False


def test_document_edit_dialog_browse_populates_local_file_path(qapp, tmp_path, monkeypatch):
    pdf_path = tmp_path / "process-sheet.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "ui.platform.admin.documents.dialogs.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(pdf_path), "Documents (*.pdf)"),
    )

    dialog = DocumentEditDialog()
    dialog._browse_for_file()

    assert dialog.storage_kind == DocumentStorageKind.FILE_PATH
    assert dialog.storage_uri == str(pdf_path)
    assert dialog.file_name == "process-sheet.pdf"


def test_document_edit_dialog_exposes_structure_and_business_version_label(qapp, services):
    structure = services["document_service"].create_document_structure(
        structure_code="PM_DOCS",
        name="Project Documents",
        object_scope="PROJECT",
        default_document_type="GENERAL",
    )
    dialog = DocumentEditDialog(structures=[structure])
    dialog.structure_combo.setCurrentIndex(dialog.structure_combo.findData(structure.id))
    dialog.revision_edit.setText("Rev A")

    assert dialog.document_structure_id == structure.id
    assert dialog.business_version_label == "Rev A"
    assert dialog.revision == "Rev A"


def test_document_admin_tab_remove_link_uses_link_selection_dialog(qapp, services):
    document = services["document_service"].create_document(
        document_code="DOC-LINK",
        title="Linked Doc",
        document_type="GENERAL",
        storage_kind="REFERENCE",
        storage_uri="vault://linked/doc-1",
    )
    link = services["document_service"].add_link(
        document_id=document.id,
        module_code="maintenance_management",
        entity_type="asset",
        entity_id="asset-001",
        link_role="reference",
    )

    tab = DocumentAdminTab(
        document_service=services["document_service"],
        user_session=services["user_session"],
    )
    qapp.processEvents()

    class _FakeDialog:
        def __init__(self, **kwargs):
            self.selected_link = link

        def exec(self):
            return 1

    import ui.platform.admin.documents.tab as document_tab_module

    original = document_tab_module.DocumentLinksDialog
    document_tab_module.DocumentLinksDialog = _FakeDialog
    try:
        tab.remove_link()
    finally:
        document_tab_module.DocumentLinksDialog = original

    assert services["document_service"].list_links(document.id) == []
