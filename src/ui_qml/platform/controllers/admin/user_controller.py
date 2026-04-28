from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.user_catalog_presenter import PlatformUserCatalogPresenter

from ..common import run_mutation, serialize_action_list


class PlatformUserController(QObject):
    usersChanged = Signal()
    userEditorOptionsChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(self, presenter: PlatformUserCatalogPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._users: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._user_editor_options: dict[str, object] = {"roleOptions": []}
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._feedback_message = ""

    @Property("QVariantMap", notify=usersChanged)
    def users(self) -> dict[str, object]:
        return self._users

    @Property("QVariantMap", notify=userEditorOptionsChanged)
    def userEditorOptions(self) -> dict[str, object]:
        return self._user_editor_options

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

    def _set_users(self, value: dict[str, object]) -> None:
        if self._users != value:
            self._users = value
            self.usersChanged.emit()

    def _set_user_editor_options(self, value: dict[str, object]) -> None:
        if self._user_editor_options != value:
            self._user_editor_options = value
            self.userEditorOptionsChanged.emit()

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

    @Slot()
    def refresh(self) -> None:
        self._refresh_users()

    @Slot("QVariantMap", result="QVariantMap")
    def createUser(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_user(dict(payload)),
            success_message="User created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateUser(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_user(dict(payload)),
            success_message="User updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleUserActive(self, user_id: str) -> dict[str, object]:
        state = self._find_item_state(self._users, user_id)
        if state is None:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.toggle_user_active(
                user_id=user_id,
                is_active=bool(state.get("isActive")),
            ),
            success_message="User active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _refresh_users(self) -> None:
        self._set_users(serialize_action_list(self._presenter.build_catalog()))
        self._set_user_editor_options(
            {
                "roleOptions": list(self._presenter.build_role_options()),
            }
        )


__all__ = ["PlatformUserController"]
