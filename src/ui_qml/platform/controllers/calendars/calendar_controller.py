from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.platform.presenters.calendars.calendar_activity_presenter import (
    PlatformCalendarActivityPresenter,
)
from src.ui_qml.platform.presenters.calendars.calendar_catalog_presenter import (
    PlatformCalendarCatalogPresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from ..common import serialize_action_list


class PlatformCalendarController(QObject):
    calendarsChanged = Signal()
    calendarSearchTextChanged = Signal()
    calendarStatusFilterChanged = Signal()
    calendarTypeFilterChanged = Signal()

    def __init__(
        self,
        presenter: PlatformCalendarCatalogPresenter,
        parent: QObject | None = None,
        *,
        activity_presenter: PlatformCalendarActivityPresenter | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._activity_presenter = activity_presenter or PlatformCalendarActivityPresenter()
        self._table_model = DynamicTableModel(self)
        self._base_catalog: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._calendars: dict[str, object] = dict(self._base_catalog)
        # Calendar cardinality per Organization is small and bounded (a
        # handful, not thousands) -- list_calendars() already returns the
        # full, unpaginated set, so search/status/type filtering is applied
        # locally over this cached unfiltered list rather than round-
        # tripping to the backend (which has no filtered list endpoint, and
        # adding one would be pagination machinery this read model doesn't
        # need).
        self._all_items: list[dict[str, object]] = []
        self._search_text = ""
        self._status_filter = ""
        self._type_filter = ""

    @Property("QVariantMap", notify=calendarsChanged)
    def calendars(self) -> dict[str, object]:
        return self._calendars

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

    @Property(str, notify=calendarSearchTextChanged)
    def calendarSearchText(self) -> str:
        return self._search_text

    @Property(str, notify=calendarStatusFilterChanged)
    def calendarStatusFilter(self) -> str:
        return self._status_filter

    @Property(str, notify=calendarTypeFilterChanged)
    def calendarTypeFilter(self) -> str:
        return self._type_filter

    @Slot()
    def refresh(self) -> None:
        self._base_catalog = serialize_action_list(self._presenter.build_catalog())
        self._all_items = list(self._base_catalog.get("items", []))
        self._apply_filters()

    @Slot(str)
    def setCalendarSearchText(self, text: str) -> None:
        normalized = str(text or "")
        if normalized == self._search_text:
            return
        self._search_text = normalized
        self.calendarSearchTextChanged.emit()
        self._apply_filters()

    @Slot(str)
    def setCalendarStatusFilter(self, status: str) -> None:
        normalized = str(status or "").strip().lower()
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self.calendarStatusFilterChanged.emit()
        self._apply_filters()

    @Slot(str)
    def setCalendarTypeFilter(self, calendar_type: str) -> None:
        normalized = str(calendar_type or "").strip().upper()
        if normalized == self._type_filter:
            return
        self._type_filter = normalized
        self.calendarTypeFilterChanged.emit()
        self._apply_filters()

    def _apply_filters(self) -> None:
        items = self._all_items
        search = self._search_text.strip().lower()
        if search:
            items = [
                item for item in items
                if search in str(item.get("title", "")).lower()
                or search in str(item.get("code", "")).lower()
            ]
        if self._status_filter:
            want_active = self._status_filter == "active"
            items = [item for item in items if bool(item.get("isActive")) == want_active]
        if self._type_filter:
            items = [item for item in items if str(item.get("calendarType", "")) == self._type_filter]

        filtered = dict(self._base_catalog)
        filtered["items"] = items
        if filtered != self._calendars:
            self._calendars = filtered
            self._table_model.set_rows(items)
            self.calendarsChanged.emit()

    def calculateCalendarWorkingDays(self, payload: dict[str, object]):
        return self._presenter.calculate_working_day(payload)

    def formatCalculationResult(self, result) -> str:
        return self._presenter.format_calculation_result(result)

    @Slot(str, str, result="QVariantList")
    def calendarActivity(self, calendar_id: str, organization_id: str) -> list[dict[str, object]]:
        normalized_calendar_id = calendar_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_calendar_id or not normalized_org_id:
            return []
        return self._activity_presenter.build_recent_activity(normalized_calendar_id, normalized_org_id)

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def calendarActivityPage(
        self,
        calendar_id: str,
        organization_id: str,
        page: int,
        page_size: int,
        search: str,
        date_range: str,
    ) -> dict[str, object]:
        normalized_calendar_id = calendar_id.strip()
        normalized_org_id = organization_id.strip()
        if not normalized_calendar_id or not normalized_org_id:
            return {"items": [], "page": page, "pageSize": page_size, "totalCount": 0, "filteredTotal": 0, "emptyState": "", "noResultsState": ""}
        return self._activity_presenter.build_activity_page_for_calendar(
            normalized_calendar_id, normalized_org_id,
            page=page, page_size=page_size, search=search, date_range=date_range,
        )


__all__ = ["PlatformCalendarController"]
