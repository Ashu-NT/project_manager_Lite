from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.platform.presenters.sites.site_catalog_presenter import PlatformSiteCatalogPresenter
from src.ui_qml.platform.presenters.sites.site_activity_presenter import PlatformSiteActivityPresenter

from src.ui_qml.platform.controllers.common import run_mutation, safe_exception_message, serialize_action_list


_SITE_PAGE_SIZE_OPTIONS = (25, 50, 100)
_DEFAULT_SITE_PAGE_SIZE = 25


class PlatformSiteController(QObject):
    sitesChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()
    siteSearchTextChanged = Signal()
    siteStatusFilterChanged = Signal()

    def __init__(
        self,
        presenter: PlatformSiteCatalogPresenter,
        parent: QObject | None = None,
        *,
        activity_presenter: PlatformSiteActivityPresenter | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._activity_presenter = activity_presenter or PlatformSiteActivityPresenter()
        self._table_model = DynamicTableModel(self)
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
        self._page = 1
        self._page_size = _DEFAULT_SITE_PAGE_SIZE
        self._search_text = ""
        self._status_filter = ""

    @Property("QVariantMap", notify=sitesChanged)
    def sites(self) -> dict[str, object]:
        return self._sites

    @Property(str, notify=siteSearchTextChanged)
    def siteSearchText(self) -> str:
        return self._search_text

    @Property(str, notify=siteStatusFilterChanged)
    def siteStatusFilter(self) -> str:
        return self._status_filter

    @Property("QVariantList", constant=True)
    def sitePageSizeOptions(self) -> list[int]:
        return list(_SITE_PAGE_SIZE_OPTIONS)

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

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
            self._table_model.set_rows(value.get("items", []))
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


    @Slot()
    def refresh(self) -> None:
        self._refresh_sites()

    @Slot(int)
    def setSitePage(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized == self._page:
            return
        self._page = normalized
        self._refresh_sites()

    @Slot(int)
    def setSitePageSize(self, page_size: int) -> None:
        normalized = int(page_size) if int(page_size) in _SITE_PAGE_SIZE_OPTIONS else _DEFAULT_SITE_PAGE_SIZE
        if normalized == self._page_size:
            return
        self._page_size = normalized
        # Changing the page size while positioned deep in the result set
        # could land past the new last page -- resetting to page 1 keeps
        # the result always valid without a second round-trip to clamp it.
        self._page = 1
        self._refresh_sites()

    @Slot(str)
    def setSiteSearchText(self, text: str) -> None:
        normalized = str(text or "")
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self._page = 1
        self.siteSearchTextChanged.emit()
        self._refresh_sites()

    @Slot(str)
    def setSiteStatusFilter(self, status: str) -> None:
        normalized = str(status or "").strip().lower()
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self._page = 1
        self.siteStatusFilterChanged.emit()
        self._refresh_sites()

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationSitesPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        """Stateless query for Organization Detail's Sites tab -- unlike
        `sites`/`refresh()` above (this controller's own shared, session-
        active-organization-scoped catalog), every call here is explicitly
        scoped to `organization_id`, regardless of which organization is
        active in the caller's session. The Sites tab owns its own
        page/pageSize/search/status state and calls this directly; no
        pagination state is stored on this controller."""
        return serialize_action_list(
            self._presenter.build_catalog_page_for_organization(
                organization_id,
                page=page,
                page_size=page_size,
                search=search,
                status=status,
            )
        )

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
    def activateSite(self, site_id: str) -> dict[str, object]:
        normalized_id = site_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.activate_site(normalized_id),
            success_message="Site activated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deactivateSite(self, site_id: str) -> dict[str, object]:
        normalized_id = site_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.deactivate_site(normalized_id),
            success_message="Site deactivated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def archiveSite(self, site_id: str) -> dict[str, object]:
        normalized_id = site_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.archive_site(normalized_id),
            success_message="Site archived.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantList")
    def siteActivity(self, site_id: str, organization_id: str) -> list[dict[str, object]]:
        normalized_site_id = site_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_site_id or not normalized_org_id:
            return []
        return self._activity_presenter.build_recent_activity(normalized_site_id, normalized_org_id)

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def siteActivityPage(
        self,
        site_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        date_range: str,
    ) -> dict[str, object]:
        normalized_site_id = site_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_site_id or not normalized_org_id:
            return {"items": [], "page": page, "pageSize": page_size, "totalCount": 0, "filteredTotal": 0, "emptyState": "", "noResultsState": ""}
        return self._activity_presenter.build_activity_page_for_site(
            normalized_site_id, normalized_org_id,
            page=page, page_size=page_size, search=search, date_range=date_range,
        )

    def _refresh_sites(self) -> None:
        self._set_sites(
            serialize_action_list(
                self._presenter.build_catalog_page(
                    page=self._page,
                    page_size=self._page_size,
                    search=self._search_text,
                    status=self._status_filter,
                )
            )
        )


__all__ = ["PlatformSiteController"]
