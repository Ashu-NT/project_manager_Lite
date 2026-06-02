from __future__ import annotations

from datetime import date

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    DesktopApiResult,
    WorkingCalendarDayDto,
    WorkingCalendarHolidayCreateCommand,
    WorkingCalendarHolidayDto,
    WorkingCalendarOptionDto,
    WorkingCalendarSnapshotDto,
    WorkingCalendarUpdateCommand,
    WorkingDayCalculationCommand,
    WorkingDayCalculationDto,
)
from src.core.platform.calendar import WorkCalendarEngine, WorkCalendarService


_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class PlatformCalendarDesktopApi:
    """Desktop-facing adapter for shared working calendar ownership."""

    def __init__(
        self,
        *,
        work_calendar_service: WorkCalendarService,
        work_calendar_engine: WorkCalendarEngine,
    ) -> None:
        self._work_calendar_service = work_calendar_service
        self._work_calendar_engine = work_calendar_engine

    def list_calendars(self) -> DesktopApiResult[tuple[WorkingCalendarOptionDto, ...]]:
        return execute_desktop_operation(
            lambda: (self._serialize_calendar_option(self._work_calendar_service.get_calendar()),)
        )

    def get_calendar_snapshot(self) -> DesktopApiResult[WorkingCalendarSnapshotDto]:
        return execute_desktop_operation(
            lambda: self._serialize_calendar_snapshot(
                self._work_calendar_service.get_calendar(),
                self._work_calendar_service.list_holidays(),
            )
        )

    def update_calendar(
        self,
        command: WorkingCalendarUpdateCommand,
    ) -> DesktopApiResult[WorkingCalendarSnapshotDto]:
        return execute_desktop_operation(
            lambda: self._serialize_calendar_snapshot(
                self._work_calendar_service.set_working_days(
                    set(command.working_days),
                    hours_per_day=command.hours_per_day,
                ),
                self._work_calendar_service.list_holidays(),
            )
        )

    def add_holiday(
        self,
        command: WorkingCalendarHolidayCreateCommand,
    ) -> DesktopApiResult[WorkingCalendarHolidayDto]:
        return execute_desktop_operation(
            lambda: self._serialize_holiday(
                self._work_calendar_service.add_holiday(
                    command.holiday_date,
                    command.name,
                )
            )
        )

    def delete_holiday(self, holiday_id: str) -> DesktopApiResult[None]:
        def _delete() -> None:
            self._work_calendar_service.delete_holiday(holiday_id)
            return None

        return execute_desktop_operation(_delete)

    def calculate_working_day(
        self,
        command: WorkingDayCalculationCommand,
    ) -> DesktopApiResult[WorkingDayCalculationDto]:
        def _calculate() -> WorkingDayCalculationDto:
            result_date = self._work_calendar_engine.add_working_days(
                command.start_date,
                command.working_days,
            )
            skipped_non_working = 0
            cursor = command.start_date
            while cursor <= result_date:
                if not self._work_calendar_engine.is_working_day(cursor):
                    skipped_non_working += 1
                cursor = date.fromordinal(cursor.toordinal() + 1)
            return WorkingDayCalculationDto(
                start_date=command.start_date,
                working_days=command.working_days,
                result_date=result_date,
                skipped_non_working_days=skipped_non_working,
            )

        return execute_desktop_operation(_calculate)

    @staticmethod
    def _serialize_calendar_option(calendar) -> WorkingCalendarOptionDto:
        working_days = set(getattr(calendar, "working_days", None) or {0, 1, 2, 3, 4})
        active_labels = [
            _DAY_LABELS[index]
            for index in range(7)
            if index in working_days
        ]
        return WorkingCalendarOptionDto(
            value=str(getattr(calendar, "id", "") or "default"),
            label=str(getattr(calendar, "name", "") or "Default Calendar").strip(),
            summary_label=(
                f"{', '.join(active_labels) or 'No days'} | "
                f"{float(getattr(calendar, 'hours_per_day', 8.0) or 8.0):g}h/day"
            ),
        )

    @staticmethod
    def _serialize_holiday(holiday) -> WorkingCalendarHolidayDto:
        return WorkingCalendarHolidayDto(
            id=str(getattr(holiday, "id", "") or ""),
            date=getattr(holiday, "date"),
            name=str(getattr(holiday, "name", "") or ""),
        )

    @classmethod
    def _serialize_calendar_snapshot(
        cls,
        calendar,
        holidays,
    ) -> WorkingCalendarSnapshotDto:
        working_days = set(getattr(calendar, "working_days", None) or {0, 1, 2, 3, 4})
        return WorkingCalendarSnapshotDto(
            id=str(getattr(calendar, "id", "") or "default"),
            name=str(getattr(calendar, "name", "") or "Default Calendar").strip(),
            working_days=tuple(
                WorkingCalendarDayDto(
                    index=day_index,
                    label=_DAY_LABELS[day_index],
                    checked=day_index in working_days,
                )
                for day_index in range(7)
            ),
            hours_per_day=float(getattr(calendar, "hours_per_day", 8.0) or 8.0),
            holidays=tuple(
                cls._serialize_holiday(holiday)
                for holiday in sorted(holidays, key=lambda item: item.date)
            ),
        )


__all__ = ["PlatformCalendarDesktopApi"]
