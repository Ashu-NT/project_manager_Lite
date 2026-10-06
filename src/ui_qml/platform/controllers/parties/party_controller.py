from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.controllers.common import (
    run_mutation,
    safe_exception_message,
    serialize_action_list,
)
from src.ui_qml.platform.presenters.parties.party_activity_presenter import (
    PlatformPartyActivityPresenter,
)
from src.ui_qml.platform.presenters.parties.party_catalog_presenter import (
    PlatformPartyCatalogPresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

_PARTY_PAGE_SIZE_OPTIONS = (25, 50, 100)
_DEFAULT_PARTY_PAGE_SIZE = 25


class PlatformPartyController(QObject):
    partiesChanged = Signal()
    partyEditorOptionsChanged = Signal()
    partySearchTextChanged = Signal()
    partyStatusFilterChanged = Signal()
    partyTypeFilterChanged = Signal()
    partyRoleFilterChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(
        self,
        presenter: PlatformPartyCatalogPresenter,
        parent: QObject | None = None,
        *,
        activity_presenter: PlatformPartyActivityPresenter | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._activity_presenter = activity_presenter or PlatformPartyActivityPresenter()
        self._table_model = DynamicTableModel(self)
        self._parties: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._party_editor_options: dict[str, object] = {"typeOptions": [], "roleOptions": []}
        self._is_busy = False
        self._error_message = ""
        self._operation_result: dict[str, object] = {
            "ok": True,
            "category": "",
            "code": "",
            "message": "",
        }
        self._feedback_message = ""
        self._page = 1
        self._page_size = _DEFAULT_PARTY_PAGE_SIZE
        self._search_text = ""
        self._status_filter = ""
        self._type_filter = ""
        self._role_filter = ""

    @Property("QVariantMap", notify=partiesChanged)
    def parties(self) -> dict[str, object]:
        return self._parties

    @Property(str, notify=partySearchTextChanged)
    def partySearchText(self) -> str:
        return self._search_text

    @Property(str, notify=partyStatusFilterChanged)
    def partyStatusFilter(self) -> str:
        return self._status_filter

    @Property(str, notify=partyTypeFilterChanged)
    def partyTypeFilter(self) -> str:
        return self._type_filter

    @Property(str, notify=partyRoleFilterChanged)
    def partyRoleFilter(self) -> str:
        return self._role_filter

    @Property("QVariantList", constant=True)
    def partyPageSizeOptions(self) -> list[int]:
        return list(_PARTY_PAGE_SIZE_OPTIONS)

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

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
            self._table_model.set_rows(value.get("items", []))
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

    @Slot(int)
    def setPartyPage(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized == self._page:
            return
        self._page = normalized
        self._refresh_parties()

    @Slot(int)
    def setPartyPageSize(self, page_size: int) -> None:
        normalized = (
            int(page_size) if int(page_size) in _PARTY_PAGE_SIZE_OPTIONS else _DEFAULT_PARTY_PAGE_SIZE
        )
        if normalized == self._page_size:
            return
        self._page_size = normalized
        # Changing the page size while positioned deep in the result set
        # could land past the new last page -- resetting to page 1 keeps
        # the result always valid without a second round-trip to clamp it.
        self._page = 1
        self._refresh_parties()

    @Slot(str)
    def setPartySearchText(self, text: str) -> None:
        normalized = str(text or "")
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self._page = 1
        self.partySearchTextChanged.emit()
        self._refresh_parties()

    @Slot(str)
    def setPartyStatusFilter(self, status: str) -> None:
        normalized = str(status or "").strip().lower()
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self._page = 1
        self.partyStatusFilterChanged.emit()
        self._refresh_parties()

    @Slot(str)
    def setPartyTypeFilter(self, party_type: str) -> None:
        normalized = str(party_type or "").strip()
        if normalized == self._type_filter:
            return
        self._type_filter = normalized
        self._page = 1
        self.partyTypeFilterChanged.emit()
        self._refresh_parties()

    @Slot(str)
    def setPartyRoleFilter(self, role: str) -> None:
        normalized = str(role or "").strip()
        if normalized == self._role_filter:
            return
        self._role_filter = normalized
        self._page = 1
        self.partyRoleFilterChanged.emit()
        self._refresh_parties()

    @Slot("QVariantMap", result=str)
    def generateCode(self, payload: dict[str, object]) -> str:
        try:
            return self._presenter.suggest_code(dict(payload))
        except Exception as exc:  # noqa: BLE001 - surface to dialog/banner
            setter = getattr(self, "_set_error_message", None)
            if setter is not None:
                setter(safe_exception_message(exc))
            return ""

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

    @Slot(str, result="QVariantMap")
    def activateParty(self, party_id: str) -> dict[str, object]:
        normalized_id = party_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.activate_party(normalized_id),
            success_message="Party activated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deactivateParty(self, party_id: str) -> dict[str, object]:
        normalized_id = party_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.deactivate_party(normalized_id),
            success_message="Party deactivated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantList")
    def partyActivity(self, party_id: str, organization_id: str) -> list[dict[str, object]]:
        normalized_party_id = party_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_party_id or not normalized_org_id:
            return []
        return self._activity_presenter.build_recent_activity(normalized_party_id, normalized_org_id)

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def partyActivityPage(
        self,
        party_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        date_range: str,
    ) -> dict[str, object]:
        normalized_party_id = party_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_party_id or not normalized_org_id:
            return {
                "items": [], "page": page, "pageSize": page_size,
                "totalCount": 0, "filteredTotal": 0, "emptyState": "", "noResultsState": "",
            }
        return self._activity_presenter.build_activity_page_for_party(
            normalized_party_id, normalized_org_id,
            page=page, page_size=page_size, search=search, date_range=date_range,
        )

    def _refresh_parties(self) -> None:
        catalog = serialize_action_list(
            self._presenter.build_catalog_page(
                page=self._page,
                page_size=self._page_size,
                search=self._search_text,
                status=self._status_filter,
                party_type=self._type_filter,
                role=self._role_filter,
            )
        )
        self._set_parties(catalog)
        self._set_party_editor_options(
            {
                "typeOptions": list(self._presenter.build_type_options()),
                "roleOptions": list(self._presenter.build_role_options()),
            }
        )


__all__ = ["PlatformPartyController"]
