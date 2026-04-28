from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.document_management_presenter import PlatformDocumentManagementPresenter

from ..common import run_mutation, serialize_action_list


class PlatformDocumentStructureController(QObject):
    documentStructuresChanged = Signal()
    documentStructureEditorOptionsChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(self, presenter: PlatformDocumentManagementPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._document_structures: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._document_structure_editor_options: dict[str, object] = {
            "parentOptions": [],
            "objectScopeOptions": [],
            "defaultTypeOptions": [],
        }
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._feedback_message = ""

    @Property("QVariantMap", notify=documentStructuresChanged)
    def documentStructures(self) -> dict[str, object]:
        return self._document_structures

    @Property("QVariantMap", notify=documentStructureEditorOptionsChanged)
    def documentStructureEditorOptions(self) -> dict[str, object]:
        return self._document_structure_editor_options

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

    @Slot()
    def refresh(self) -> None:
        catalog, editor_options = self._presenter.build_structure_management()
        self._set_document_structures(serialize_action_list(catalog))
        self._set_document_structure_editor_options(dict(editor_options))

    @Slot("QVariantMap", result="QVariantMap")
    def createDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_document_structure(dict(payload)),
            success_message="Document structure created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_document_structure(dict(payload)),
            success_message="Document structure updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleDocumentStructureActive(self, structure_id: str) -> dict[str, object]:
        state = self._find_item_state(self._document_structures, structure_id)
        if state is None:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.toggle_document_structure_active(
                structure_id=structure_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Document structure active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _set_document_structures(self, value: dict[str, object]) -> None:
        if self._document_structures != value:
            self._document_structures = value
            self.documentStructuresChanged.emit()

    def _set_document_structure_editor_options(self, value: dict[str, object]) -> None:
        if self._document_structure_editor_options != value:
            self._document_structure_editor_options = value
            self.documentStructureEditorOptionsChanged.emit()

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

    @staticmethod
    def _find_item_state(items: dict[str, object], item_id: str) -> dict[str, object] | None:
        normalized_id = item_id.strip()
        if not normalized_id:
            return None
        for item in items.get("items", []):
            if isinstance(item, dict) and item.get("id") == normalized_id:
                return dict(item.get("state") or {})
        return None

    @staticmethod
    def _to_int(value: object) -> int | None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


__all__ = ["PlatformDocumentStructureController"]
