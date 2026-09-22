from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)
from src.ui_qml.platform.presenters.organizations.organization_activity_presenter import (
    PlatformOrganizationActivityPresenter,
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
    organizationStatusFilterChanged = Signal()
    selectedOrganizationIdsChanged = Signal()

    def __init__(
        self,
        presenter: PlatformOrganizationCatalogPresenter,
        parent: QObject | None = None,
        *,
        activity_presenter: PlatformOrganizationActivityPresenter | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._activity_presenter = activity_presenter or PlatformOrganizationActivityPresenter()
        self._table_model = DynamicTableModel(self)
        self._organizations: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._organization_editor_options: dict[str, object] = {
            "moduleOptions": [], "countryOptions": [], "timezoneOptions": [], "currencyOptions": [],
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
        self._page = 1
        self._page_size = _DEFAULT_ORGANIZATION_PAGE_SIZE
        self._search_text = ""
        self._status_filter = ""
        self._selected_organization_ids: list[str] = []

    @Property("QVariantMap", notify=organizationsChanged)
    def organizations(self) -> dict[str, object]:
        return self._organizations

    @Property(str, notify=organizationSearchTextChanged)
    def organizationSearchText(self) -> str:
        return self._search_text

    @Property(str, notify=organizationStatusFilterChanged)
    def organizationStatusFilter(self) -> str:
        return self._status_filter

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

    @Property("QVariantList", notify=selectedOrganizationIdsChanged)
    def selectedOrganizationIds(self) -> list[str]:
        return list(self._selected_organization_ids)

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

    def _set_selected_organization_ids(self, value: list[str]) -> None:
        if value != self._selected_organization_ids:
            self._selected_organization_ids = value
            self.selectedOrganizationIdsChanged.emit()

    @Slot()
    def refresh(self) -> None:
        self._refresh_organizations()
        self._set_organization_editor_options(
            {
                "moduleOptions": list(self._presenter.build_module_options()),
                "countryOptions": list(self._presenter.build_country_options()),
                "timezoneOptions": list(self._presenter.build_timezone_options()),
                "currencyOptions": list(self._presenter.build_currency_options()),
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

    @Slot(str)
    def setOrganizationStatusFilter(self, status: str) -> None:
        normalized = str(status or "").strip().lower()
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self._page = 1
        self.organizationStatusFilterChanged.emit()
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
    def organizationActivity(self, organization_id: str) -> list[dict[str, object]]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return []
        return self._presenter.build_recent_activity(normalized_id)

    @Slot(str, int, int, str, str, str, result="QVariantMap")
    def organizationActivityPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        entity_type: str,
        date_range: str,
    ) -> dict[str, object]:
        """Full, paginated + searchable Activity workspace for Organization
        Detail's Activity tab -- unlike `organizationActivity` above (this
        controller's bounded ~5-item Overview preview), explicitly scoped
        to `organization_id` with server-side search/type/date filters and
        stable pagination. No pagination state is stored on this
        controller; the Activity tab owns its own state and calls this
        directly."""
        normalized_id = organization_id.strip()
        if not normalized_id:
            return {"items": [], "page": page, "pageSize": page_size, "totalCount": 0, "filteredTotal": 0, "emptyState": "", "noResultsState": ""}
        return self._activity_presenter.build_activity_page_for_organization(
            normalized_id,
            page=page,
            page_size=page_size,
            search=search,
            entity_type=entity_type,
            date_range=date_range,
        )

    @Slot("QVariantMap", result=str)
    def generateCode(self, payload: dict[str, object]) -> str:
        """Return a suggested unique organization code for the editor dialog."""
        try:
            return self._presenter.suggest_code(dict(payload))
        except Exception as exc:  # surface generation errors via the dialog/banner
            self._set_error_message(safe_exception_message(exc))
            return ""

    @Slot(str, result="QVariantMap")
    def activateOrganization(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.activate_organization(normalized_id),
            success_message="Organization activated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deactivateOrganization(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.deactivate_organization(normalized_id),
            success_message="Organization deactivated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def archiveOrganization(self, organization_id: str) -> dict[str, object]:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.archive_organization(normalized_id),
            success_message="Organization archived.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    # ------------------------------------------------------------------
    # Row-selection state (bulk actions) -- selection persists across page/
    # search changes so a multi-page selection survives paging; it's only
    # cleared once a bulk action actually applies.
    # ------------------------------------------------------------------

    @Slot(str, bool)
    def setOrganizationBulkSelection(self, organization_id: str, selected: bool) -> None:
        normalized_id = organization_id.strip()
        if not normalized_id:
            return
        current = list(self._selected_organization_ids)
        if selected:
            if normalized_id not in current:
                current.append(normalized_id)
        elif normalized_id in current:
            current.remove(normalized_id)
        self._set_selected_organization_ids(current)

    @Slot()
    def clearOrganizationBulkSelection(self) -> None:
        self._set_selected_organization_ids([])

    @Slot()
    def selectVisibleOrganizations(self) -> None:
        items = self._organizations.get("items", [])
        self._set_selected_organization_ids([str(item.get("id", "")) for item in items if item.get("id")])

    def _clear_selection_and_refresh(self) -> None:
        self._set_selected_organization_ids([])
        self.refresh()

    # ------------------------------------------------------------------
    # Bulk actions -- each applies to every currently-selected organization.
    # ------------------------------------------------------------------

    def _apply_bulk_organization_status(self, *, status: str, verb: str) -> dict[str, object]:
        ids = list(self._selected_organization_ids)
        return run_mutation(
            operation=lambda: self._presenter.bulk_set_organization_status(ids, status=status),
            success_message=f"{len(ids)} organization(s) {verb}.",
            on_success=self._clear_selection_and_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(result="QVariantMap")
    def bulkActivateOrganizations(self) -> dict[str, object]:
        return self._apply_bulk_organization_status(status="active", verb="activated")

    @Slot(result="QVariantMap")
    def bulkDeactivateOrganizations(self) -> dict[str, object]:
        return self._apply_bulk_organization_status(status="inactive", verb="deactivated")

    @Slot(result="QVariantMap")
    def bulkArchiveOrganizations(self) -> dict[str, object]:
        return self._apply_bulk_organization_status(status="archived", verb="archived")

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationCurrency(self, payload: dict[str, object]) -> dict[str, object]:
        base_currency = str(payload.get("value", "")).strip()
        ids = list(self._selected_organization_ids)
        return run_mutation(
            operation=lambda: self._presenter.bulk_update_organization_currency(ids, base_currency),
            success_message=f"Currency updated for {len(ids)} organization(s).",
            on_success=self._clear_selection_and_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationTimezone(self, payload: dict[str, object]) -> dict[str, object]:
        timezone_name = str(payload.get("value", "")).strip()
        ids = list(self._selected_organization_ids)
        return run_mutation(
            operation=lambda: self._presenter.bulk_update_organization_timezone(ids, timezone_name),
            success_message=f"Timezone updated for {len(ids)} organization(s).",
            on_success=self._clear_selection_and_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkOrganizationModules(self, payload: dict[str, object]) -> dict[str, object]:
        module_codes = [str(code) for code in (payload.get("moduleCodes") or []) if str(code).strip()]
        grant = bool(payload.get("grant", True))
        ids = list(self._selected_organization_ids)
        return run_mutation(
            operation=lambda: self._presenter.bulk_assign_modules(ids, module_codes, grant=grant),
            success_message=(
                f"{'Granted' if grant else 'Revoked'} {len(module_codes)} module(s) "
                f"for {len(ids)} organization(s)."
            ),
            on_success=self._clear_selection_and_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    def _refresh_organizations(self) -> None:
        self._set_organizations(
            serialize_action_list(
                self._presenter.build_catalog_page(
                    page=self._page,
                    page_size=self._page_size,
                    search=self._search_text,
                    status=self._status_filter or None,
                )
            )
        )


__all__ = ["PlatformOrganizationController"]
