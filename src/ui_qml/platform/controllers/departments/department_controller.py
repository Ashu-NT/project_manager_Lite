from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.controllers.common import (
    run_history_preview,
    run_mutation,
    safe_exception_message,
    serialize_action_list,
)
from src.ui_qml.platform.presenters.departments.department_activity_presenter import (
    PlatformDepartmentActivityPresenter,
)
from src.ui_qml.platform.presenters.departments.department_catalog_presenter import (
    PlatformDepartmentCatalogPresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

_DEPARTMENT_PAGE_SIZE_OPTIONS = (25, 50, 100)
_DEFAULT_DEPARTMENT_PAGE_SIZE = 25


class PlatformDepartmentController(QObject):
    departmentsChanged = Signal()
    departmentEditorOptionsChanged = Signal()
    departmentSearchTextChanged = Signal()
    departmentStatusFilterChanged = Signal()
    departmentSiteFilterChanged = Signal()
    isBusyChanged = Signal()
    errorMessageChanged = Signal()
    operationResultChanged = Signal()
    feedbackMessageChanged = Signal()

    def __init__(
        self,
        presenter: PlatformDepartmentCatalogPresenter,
        parent: QObject | None = None,
        *,
        activity_presenter: PlatformDepartmentActivityPresenter | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._activity_presenter = activity_presenter or PlatformDepartmentActivityPresenter()
        self._table_model = DynamicTableModel(self)
        self._departments: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._department_editor_options: dict[str, object] = {
            "siteOptions": [],
            "parentOptions": [],
            "headOfDepartmentOptions": [],
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
        self._page_size = _DEFAULT_DEPARTMENT_PAGE_SIZE
        self._search_text = ""
        self._status_filter = ""
        self._site_filter = ""

    @Property("QVariantMap", notify=departmentsChanged)
    def departments(self) -> dict[str, object]:
        return self._departments

    @Property(str, notify=departmentSearchTextChanged)
    def departmentSearchText(self) -> str:
        return self._search_text

    @Property(str, notify=departmentStatusFilterChanged)
    def departmentStatusFilter(self) -> str:
        return self._status_filter

    @Property(str, notify=departmentSiteFilterChanged)
    def departmentSiteFilter(self) -> str:
        return self._site_filter

    @Property("QVariantList", constant=True)
    def departmentPageSizeOptions(self) -> list[int]:
        return list(_DEPARTMENT_PAGE_SIZE_OPTIONS)

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

    @Property("QVariantMap", notify=departmentEditorOptionsChanged)
    def departmentEditorOptions(self) -> dict[str, object]:
        return self._department_editor_options

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

    def _set_departments(self, value: dict[str, object]) -> None:
        if self._departments != value:
            self._departments = value
            self._table_model.set_rows(value.get("items", []))
            self.departmentsChanged.emit()

    def _set_department_editor_options(self, value: dict[str, object]) -> None:
        if self._department_editor_options != value:
            self._department_editor_options = value
            self.departmentEditorOptionsChanged.emit()

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
        self._refresh_departments()

    @Slot(int)
    def setDepartmentPage(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized == self._page:
            return
        self._page = normalized
        self._refresh_departments()

    @Slot(int)
    def setDepartmentPageSize(self, page_size: int) -> None:
        normalized = (
            int(page_size) if int(page_size) in _DEPARTMENT_PAGE_SIZE_OPTIONS else _DEFAULT_DEPARTMENT_PAGE_SIZE
        )
        if normalized == self._page_size:
            return
        self._page_size = normalized
        # Changing the page size while positioned deep in the result set
        # could land past the new last page -- resetting to page 1 keeps
        # the result always valid without a second round-trip to clamp it.
        self._page = 1
        self._refresh_departments()

    @Slot(str)
    def setDepartmentSearchText(self, text: str) -> None:
        normalized = str(text or "")
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self._page = 1
        self.departmentSearchTextChanged.emit()
        self._refresh_departments()

    @Slot(str)
    def setDepartmentStatusFilter(self, status: str) -> None:
        normalized = str(status or "").strip().lower()
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self._page = 1
        self.departmentStatusFilterChanged.emit()
        self._refresh_departments()

    @Slot(str)
    def setDepartmentSiteFilter(self, site_id: str) -> None:
        normalized = str(site_id or "").strip()
        if normalized == self._site_filter:
            return
        self._site_filter = normalized
        self._page = 1
        self.departmentSiteFilterChanged.emit()
        self._refresh_departments()

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationDepartmentsPage(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        """Stateless query for Organization Detail's Departments tab --
        unlike `departments`/`refresh()` above (this controller's own
        shared, session-active-organization-scoped catalog), every call
        here is explicitly scoped to `organization_id`, regardless of
        which organization is active in the caller's session. The
        Departments tab owns its own page/pageSize/search/status state and
        calls this directly; no pagination state is stored on this
        controller."""
        return serialize_action_list(
            self._presenter.build_catalog_page_for_organization(
                organization_id,
                page=page,
                page_size=page_size,
                search=search,
                status=status,
            )
        )

    @Slot(str, result="QVariantMap")
    def departmentsForSite(self, site_id: str) -> dict[str, object]:
        return serialize_action_list(self._presenter.build_catalog_for_site(site_id))

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def departmentsForSitePage(
        self,
        site_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        status: str,
    ) -> dict[str, object]:
        """Stateless, paginated counterpart to departmentsForSite() above,
        for Site Detail's canonical DataTable Departments tab. Mirrors
        organizationDepartmentsPage()'s stateless-query shape exactly; no
        pagination state is stored on this controller."""
        return serialize_action_list(
            self._presenter.build_catalog_page_for_site(
                site_id,
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
    def createDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_department(dict(payload)),
            success_message="Department created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDepartment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_department(dict(payload)),
            success_message="Department updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def activateDepartment(self, department_id: str) -> dict[str, object]:
        normalized_id = department_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.activate_department(normalized_id),
            success_message="Department activated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deactivateDepartment(self, department_id: str) -> dict[str, object]:
        normalized_id = department_id.strip()
        if not normalized_id:
            return dict(self.operationResult)
        return run_mutation(
            operation=lambda: self._presenter.deactivate_department(normalized_id),
            success_message="Department deactivated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_operation_result=self._set_operation_result,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantList")
    def departmentActivity(self, department_id: str, organization_id: str) -> list[dict[str, object]]:
        normalized_department_id = department_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_department_id or not normalized_org_id:
            return []
        return run_history_preview(
            operation=lambda: self._activity_presenter.build_recent_activity(
                normalized_department_id, normalized_org_id
            ),
            set_error_message=self._set_error_message,
            label="department activity",
        )

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def departmentActivityPage(
        self,
        department_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        date_range: str,
    ) -> dict[str, object]:
        normalized_department_id = department_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_department_id or not normalized_org_id:
            return {
                "items": [], "page": page, "pageSize": page_size,
                "totalCount": 0, "filteredTotal": 0, "emptyState": "", "noResultsState": "",
            }
        return self._activity_presenter.build_activity_page_for_department(
            normalized_department_id, normalized_org_id,
            page=page, page_size=page_size, search=search, date_range=date_range,
        )

    @Slot(str, result="QVariantMap")
    def headOfDepartmentOptionsFor(self, department_id: str) -> dict[str, object]:
        """Edit-only, computed fresh per call (never cached on this
        controller) -- HOD candidates are scoped to this exact department,
        unlike the org-wide site/parent options in departmentEditorOptions."""
        return {"headOfDepartmentOptions": list(self._presenter.build_head_of_department_options(department_id))}

    def _refresh_departments(self) -> None:
        catalog = serialize_action_list(
            self._presenter.build_catalog_page(
                page=self._page,
                page_size=self._page_size,
                search=self._search_text,
                status=self._status_filter,
                site_id=self._site_filter,
            )
        )
        self._set_departments(catalog)
        self._set_department_editor_options(
            {
                "siteOptions": list(self._presenter.build_site_options()),
                "parentOptions": list(self._presenter.build_parent_options()),
                "headOfDepartmentOptions": list(self._presenter.build_head_of_department_options()),
            }
        )


__all__ = ["PlatformDepartmentController"]
