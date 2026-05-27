from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.party_catalog_presenter import PlatformPartyCatalogPresenter

from ..common import run_mutation, serialize_action_list


class PlatformPartyController(QObject):
    partiesChanged = Signal()
    partyEditorOptionsChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(self, presenter: PlatformPartyCatalogPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._parties: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._party_editor_options: dict[str, object] = {"typeOptions": []}
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._feedback_message = ""

    @Property("QVariantMap", notify=partiesChanged)
    def parties(self) -> dict[str, object]:
        return self._parties

    @Property("QVariantMap", notify=partyEditorOptionsChanged)
    def partyEditorOptions(self) -> dict[str, object]:
        return self._party_editor_options

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

    def _set_parties(self, value: dict[str, object]) -> None:
        if self._parties != value:
            self._parties = value
            self.partiesChanged.emit()

    def _set_party_editor_options(self, value: dict[str, object]) -> None:
        if self._party_editor_options != value:
            self._party_editor_options = value
            self.partyEditorOptionsChanged.emit()

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
                return dict(item.get("state") or {})
        return None

    def _to_int(self, value: object) -> int | None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @Slot()
    def refresh(self) -> None:
        self._refresh_parties()

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_party(dict(payload)),
            success_message="Party created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_party(dict(payload)),
            success_message="Party updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        state = self._find_item_state(self._parties, party_id)
        if state is None:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.toggle_party_active(
                party_id=party_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Party active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _refresh_parties(self) -> None:
        self._set_parties(serialize_action_list(self._presenter.build_catalog()))
        self._set_party_editor_options(
            {
                "typeOptions": list(self._presenter.build_type_options()),
            }
        )


__all__ = ["PlatformPartyController"]
