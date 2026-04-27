from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.document_catalog_presenter import PlatformDocumentCatalogPresenter

from ..common import run_mutation, serialize_action_list


class PlatformDocumentController(QObject):
    documentsChanged = Signal()
    documentEditorOptionsChanged = Signal()
    selectedDocumentChanged = Signal()
    documentPreviewChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(self, presenter: PlatformDocumentCatalogPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._documents: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._document_editor_options: dict[str, object] = {}
        self._selected_document: dict[str, object] = {
            "hasSelection": False,
            "documentId": "",
            "title": "Select a document",
            "summary": "",
            "badges": [],
            "metadataRows": [],
            "notes": "",
        }
        self._document_preview: dict[str, object] = {
            "statusLabel": "No document selected",
            "summary": "",
            "canOpen": False,
            "openLabel": "Open Source",
            "openTargetUrl": "",
        }
        self._selected_document_id = ""
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {"success": False}
        self._feedback_message = ""

    @Property("QVariantMap", notify=documentsChanged)
    def documents(self) -> dict[str, object]:
        return self._documents

    @Property("QVariantMap", notify=documentEditorOptionsChanged)
    def documentEditorOptions(self) -> dict[str, object]:
        return self._document_editor_options

    @Property("QVariantMap", notify=selectedDocumentChanged)
    def selectedDocument(self) -> dict[str, object]:
        return self._selected_document

    @Property("QVariantMap", notify=documentPreviewChanged)
    def documentPreview(self) -> dict[str, object]:
        return self._document_preview

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property("QVariantMap", notify=operationResultChanged)
    def operationResult(self) -> dict[str, object]:
        return self._operation_result

    @Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._feedback_message

    def _set_documents(self, value: dict[str, object]) -> None:
        if self._documents != value:
            self._documents = value
            self.documentsChanged.emit()

    def _set_document_editor_options(self, value: dict[str, object]) -> None:
        if self._document_editor_options != value:
            self._document_editor_options = value
            self.documentEditorOptionsChanged.emit()

    def _set_selected_document(self, value: dict[str, object]) -> None:
        if self._selected_document != value:
            self._selected_document = value
            self.selectedDocumentChanged.emit()

    def _set_document_preview(self, value: dict[str, object]) -> None:
        if self._document_preview != value:
            self._document_preview = value
            self.documentPreviewChanged.emit()

    def _set_is_busy(self, value: bool) -> None:
        if self._is_busy != value:
            self._is_busy = value
            self.isBusyChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if self._error_message != value:
            self._error_message = value
            self.errorMessageChanged.emit()

    def _set_operation_result(self, value: dict[str, object]) -> None:
        if self._operation_result != value:
            self._operation_result = value
            self.operationResultChanged.emit()

    def _set_feedback_message(self, value: str) -> None:
        if self._feedback_message != value:
            self._feedback_message = value
            self.feedbackMessageChanged.emit()

    def _find_item_state(self, items: dict[str, object], item_id: str) -> dict[str, object] | None:
        items_list = items.get("items", [])
        if not isinstance(items_list, list):
            return None
        for item in items_list:
            if isinstance(item, dict) and item.get("id") == item_id:
                return item
        return None

    def _to_int(self, value: object) -> int | None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @Slot()
    def refresh(self) -> None:
        self._refresh_documents()

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_document(dict(payload)),
            success_message="Document created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
            success_result_handler=self._select_document_from_result,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_document(dict(payload)),
            success_message="Document updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
            success_result_handler=self._select_document_from_result,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        state = self._find_item_state(self._documents, document_id)
        if state is None:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.toggle_document_active(
                document_id=document_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Document active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
            success_result_handler=self._select_document_from_result,
        )

    @Slot(str)
    def selectDocument(self, document_id: str) -> None:
        normalized_id = document_id.strip()
        if not normalized_id:
            return
        self._selected_document_id = normalized_id
        self._refresh_document_focus()

    def _refresh_documents(self) -> None:
        catalog = serialize_action_list(self._presenter.build_catalog())
        self._set_documents(catalog)
        self._set_document_editor_options(
            {
                "classificationOptions": list(self._presenter.build_classification_options()),
            }
        )

    def _refresh_document_focus(self) -> None:
        if self._selected_document_id:
            selected = self._presenter.build_document_focus(self._selected_document_id)
            self._set_selected_document(selected.get("selectedDocument", {}))
            self._set_document_preview(selected.get("documentPreview", {}))

    def _select_document_from_result(self, result: object) -> None:
        if isinstance(result, dict):
            doc_id = result.get("id")
            if doc_id:
                self.selectDocument(str(doc_id))


__all__ = ["PlatformDocumentController"]
__all__ = ["PlatformDocumentController"]