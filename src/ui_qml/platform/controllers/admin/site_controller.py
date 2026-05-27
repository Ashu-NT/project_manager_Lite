from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.site_catalog_presenter import PlatformSiteCatalogPresenter

from ..common import run_mutation, serialize_action_list


class PlatformSiteController(QObject):
    sitesChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(self, presenter: PlatformSiteCatalogPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._sites: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._feedback_message = ""

    @Property("QVariantMap", notify=sitesChanged)
    def sites(self) -> dict[str, object]:
        return self._sites

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

    def _set_sites(self, value: dict[str, object]) -> None:
        if self._sites != value:
            self._sites = value
            self.sitesChanged.emit()

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
        self._refresh_sites()

    @Slot("QVariantMap", result="QVariantMap")
    def createSite(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_site(dict(payload)),
            success_message="Site created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateSite(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_site(dict(payload)),
            success_message="Site updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def toggleSiteActive(self, site_id: str) -> dict[str, object]:
        state = self._find_item_state(self._sites, site_id)
        if state is None:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.toggle_site_active(
                site_id=site_id,
                is_active=bool(state.get("isActive")),
                expected_version=self._to_int(state.get("version")),
            ),
            success_message="Site active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _refresh_sites(self) -> None:
        self._set_sites(serialize_action_list(self._presenter.build_catalog()))


__all__ = ["PlatformSiteController"]
