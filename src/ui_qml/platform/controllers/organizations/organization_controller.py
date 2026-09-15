from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)

from src.ui_qml.platform.controllers.common import run_mutation, safe_exception_message, serialize_action_list


_ORGANIZATION_PAGE_SIZE_OPTIONS = (25, 50, 100)
_DEFAULT_ORGANIZATION_PAGE_SIZE = 25


class PlatformOrganizationController(QObject):
    organizationsChanged = Signal()
    organizationEditorOptionsChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()
    organizationSearchTextChanged = Signal()

    def __init__(self, presenter: PlatformOrganizationCatalogPresenter, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._table_model = DynamicTableModel(self)
        self._organizations: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._organization_editor_options: dict[str, object] = {"moduleOptions": [], "countryOptions": []}
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
        self._page_size = _DEFAULT_ORGANIZATION_PAGE_SIZE
        self._search_text = ""

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organizations

    @Property(str, notify=organizationSearchTextChanged)
    def organizationSearchText(self) -> str:
        return self._search_text

    @Property("QVariantList", constant=True)
    def organizationPageSizeOptions(self) -> list[int]:
        return list(_ORGANIZATION_PAGE_SIZE_OPTIONS)

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

    @Property("QVariantMap", notify=organizationEditorOptionsChanged)
    def organizationEditorOptions(self) -> dict[str, object]:
        return self._organization_editor_options

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

    def _set_organizations(self, value: dict[str, object]) -> None:
        if self._organizations != value:
            self._organizations = value
            self._table_model.set_rows(value.get("items", []))
            self.organizationsChanged.emit()

    def _set_organization_editor_options(self, value: dict[str, object]) -> None:
        if self._organization_editor_options != value:
            self._organization_editor_options = value
            self.organizationEditorOptionsChanged.emit()

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

    @Slot()
    def refresh(self) -> None:
        self._refresh_organizations()
        self._set_organization_editor_options(
            {
                "moduleOptions": list(self._presenter.build_module_options()),
                "countryOptions": list(self._presenter.build_country_options()),
            }
        )

    def refresh_organizations(self) -> None:
        """Narrow reaction to the organization-collection ViewInvalidation target -- re-reads
        only the organization list, unlike `refresh()`'s full reload (module options too),
        which is not stale after a plain organization creation."""
        self._refresh_organizations()

    @Slot(int)
    def setOrganizationPage(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized == self._page:
            return
        self._page = normalized
        self._refresh_organizations()

    @Slot(int)
    def setOrganizationPageSize(self, page_size: int) -> None:
        normalized = int(page_size) if int(page_size) in _ORGANIZATION_PAGE_SIZE_OPTIONS else _DEFAULT_ORGANIZATION_PAGE_SIZE
        if normalized == self._page_size:
            return
        self._page_size = normalized
        # Changing the page size while positioned deep in the result set
        # could land past the new last page -- resetting to page 1 keeps
        # the result always valid without a second round-trip to clamp it.
        self._page = 1
        self._refresh_organizations()

    @Slot(str)
    def setOrganizationSearchText(self, text: str) -> None:
        normalized = str(text or "")
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self._page = 1
        self.organizationSearchTextChanged.emit()
        self._refresh_organizations()

    @Slot("QVariantMap", result="QVariantMap")
    def createOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_organization(dict(payload)),
            success_message="Organization created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateOrganization(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_organization(dict(payload)),
            success_message="Organization updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def organizationDetailContext(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return {"statistics": {}, "recentActivity": []}
        return self._presenter.build_detail_context(normalized_id)

    @Slot(str, result="QVariantList")
    def organizationAuditActivity(self, organization_id: str) -> list[dict[str, object]]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return []
        return self._presenter.build_audit_activity(normalized_id)

    @Slot("QVariantMap", result=str)
    def generateCode(self, payload: dict[str, object]) -> str:
        """Return a suggested unique organization code for the editor dialog."""
        try:
            return self._presenter.suggest_code(dict(payload))
        except Exception as exc:  # surface generation errors via the dialog/banner
            self._set_error_message(safe_exception_message(exc))
            return ""

    @Slot(str, result="QVariantMap")
    def enableOrganization(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.enable_organization(normalized_id),
            success_message="Organization enabled.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _refresh_organizations(self) -> None:
        self._set_organizations(
            serialize_action_list(
                self._presenter.build_catalog_page(
                    page=self._page, page_size=self._page_size, search=self._search_text
                )
            )
        )


__all__ = ["PlatformOrganizationController"]
