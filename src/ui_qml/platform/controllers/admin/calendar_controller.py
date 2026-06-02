from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.platform.presenters.calendar_catalog_presenter import PlatformCalendarCatalogPresenter

from ..common import serialize_action_list


class PlatformCalendarController(QObject):
    calendarsChanged = Signal()

    def __init__(
        self,
        presenter: PlatformCalendarCatalogPresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._table_model = DynamicTableModel(self)
        self._calendars: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }

    @Property("QVariantMap", notify=calendarsChanged)
    def calendars(self) -> dict[str, object]:
        return self._calendars

    @Property(QObject, constant=True)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

    @Slot()
    def refresh(self) -> None:
        catalog = serialize_action_list(self._presenter.build_catalog())
        if catalog != self._calendars:
            self._calendars = catalog
            self._table_model.set_rows(catalog.get("items", []))
            self.calendarsChanged.emit()

    def updateCalendar(self, payload: dict[str, object]):
        return self._presenter.update_calendar(payload)

    def addCalendarHoliday(self, payload: dict[str, object]):
        return self._presenter.add_holiday(payload)

    def deleteCalendarHoliday(self, holiday_id: str):
        return self._presenter.delete_holiday(holiday_id)

    def calculateCalendarWorkingDays(self, payload: dict[str, object]):
        return self._presenter.calculate_working_day(payload)

    def formatCalculationResult(self, result) -> str:
        return self._presenter.format_calculation_result(result)


__all__ = ["PlatformCalendarController"]
