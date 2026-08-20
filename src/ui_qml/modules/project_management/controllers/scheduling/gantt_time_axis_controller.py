"""Display-only calendar axis state for the integrated Gantt viewport."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from math import ceil, floor
from typing import Callable, Iterable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.modules.project_management.api.desktop.scheduling.models import (
    GanttBaselineOverlayDto,
    GanttProjectionDto,
)


QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

_TIMESCALE_BASE_DENSITY = {
    "day": 40.0,
    "week": 12.0,
    "month": 4.0,
    "quarter": 1.5,
}
_ZOOM_LEVELS = (0.75, 0.875, 1.0, 1.25, 1.5)
_NEUTRAL_ZOOM_INDEX = 2


@QmlElement
@QmlUncreatable("Gantt time-axis state is provided by the Scheduling workspace.")
class GanttTimeAxisController(QObject):
    configurationChanged = Signal()
    viewportChanged = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        super().__init__(parent)
        self._today_provider = today_provider
        self._timescale = "week"
        self._zoom_index = _NEUTRAL_ZOOM_INDEX
        self._base_start_day = -1
        self._base_finish_day = -1
        self._projection_project_id = ""
        self._projection_start_day = -1
        self._projection_finish_day = -1
        self._baseline_start_day = -1
        self._baseline_finish_day = -1
        self._range_start_day = -1
        self._range_finish_day = -1
        self._viewport_content_x = 0.0
        self._viewport_width = 1200.0
        self._visible_start_day = -1
        self._visible_finish_day = -1
        self._major_ticks: list[dict[str, object]] = []
        self._minor_ticks: list[dict[str, object]] = []
        self._calendar_shading_authoritative = False
        self._all_non_working_intervals: tuple[tuple[int, int], ...] = ()
        self._visible_non_working_intervals: list[dict[str, int]] = []

    @Property(str, notify=configurationChanged)
    def timescale(self) -> str:
        return self._timescale

    @Property("QVariantList", constant=True)
    def timescaleOptions(self) -> list[dict[str, str]]:
        return [
            {"value": value, "label": value.title()}
            for value in _TIMESCALE_BASE_DENSITY
        ]

    @Property("QVariantList", constant=True)
    def zoomLevels(self) -> list[float]:
        return list(_ZOOM_LEVELS)

    @Property(int, notify=configurationChanged)
    def zoomIndex(self) -> int:
        return self._zoom_index

    @Property(float, notify=configurationChanged)
    def zoomMultiplier(self) -> float:
        return _ZOOM_LEVELS[self._zoom_index]

    @Property(bool, notify=configurationChanged)
    def canZoomIn(self) -> bool:
        return self.hasRange and self._zoom_index < len(_ZOOM_LEVELS) - 1

    @Property(bool, notify=configurationChanged)
    def canZoomOut(self) -> bool:
        return self.hasRange and self._zoom_index > 0

    @Property(bool, notify=configurationChanged)
    def canResetZoom(self) -> bool:
        return self.hasRange and self._zoom_index != _NEUTRAL_ZOOM_INDEX

    @Property(bool, notify=configurationChanged)
    def hasRange(self) -> bool:
        return self._range_start_day > 0 and self._range_finish_day >= self._range_start_day

    @Property(int, notify=configurationChanged)
    def baseRangeStartDay(self) -> int:
        return self._base_start_day

    @Property(int, notify=configurationChanged)
    def baseRangeFinishDay(self) -> int:
        return self._base_finish_day

    @Property(int, notify=configurationChanged)
    def rangeStartDay(self) -> int:
        return self._range_start_day

    @Property(int, notify=configurationChanged)
    def rangeFinishDay(self) -> int:
        return self._range_finish_day

    @Property(int, notify=configurationChanged)
    def rangeDayCount(self) -> int:
        if not self.hasRange:
            return 0
        return self._range_finish_day - self._range_start_day + 1

    @Property(float, notify=configurationChanged)
    def pixelsPerDay(self) -> float:
        return _TIMESCALE_BASE_DENSITY[self._timescale] * self.zoomMultiplier

    @Property(float, notify=configurationChanged)
    def contentWidth(self) -> float:
        return self.rangeDayCount * self.pixelsPerDay

    @Property(str, notify=configurationChanged)
    def rangeWarning(self) -> str:
        if self.contentWidth <= 16_000_000:
            return ""
        return "This timeline is extremely wide. Use Month or Quarter for safer navigation."

    @Property(int, notify=viewportChanged)
    def visibleStartDay(self) -> int:
        return self._visible_start_day

    @Property(int, notify=viewportChanged)
    def visibleFinishDay(self) -> int:
        return self._visible_finish_day

    @Property("QVariantList", notify=viewportChanged)
    def majorTicks(self) -> list[dict[str, object]]:
        return list(self._major_ticks)

    @Property("QVariantList", notify=viewportChanged)
    def minorTicks(self) -> list[dict[str, object]]:
        return list(self._minor_ticks)

    @Property(bool, notify=configurationChanged)
    def calendarShadingAuthoritative(self) -> bool:
        return self._calendar_shading_authoritative

    @Property("QVariantList", notify=viewportChanged)
    def visibleNonWorkingIntervals(self) -> list[dict[str, int]]:
        return list(self._visible_non_working_intervals)

    @Property(int, notify=configurationChanged)
    def todayDay(self) -> int:
        return self._today_provider().toordinal()

    @Property(bool, notify=configurationChanged)
    def todayAvailable(self) -> bool:
        return self.hasRange and self._range_start_day <= self.todayDay <= self._range_finish_day

    @Property(str, notify=configurationChanged)
    def todayUnavailableReason(self) -> str:
        if not self.hasRange:
            return "No scheduled date range is available."
        if not self.todayAvailable:
            return "Today is outside this schedule."
        return ""

    def set_projection(self, projection: GanttProjectionDto | None) -> None:
        base_start = projection.range_start_day_ordinal if projection else None
        base_finish = projection.range_finish_day_ordinal if projection else None
        self._projection_project_id = projection.project_id if projection else ""
        self._projection_start_day = int(base_start) if base_start is not None else -1
        self._projection_finish_day = int(base_finish) if base_finish is not None else -1
        self._baseline_start_day = -1
        self._baseline_finish_day = -1
        self._calendar_shading_authoritative = bool(
            projection and projection.calendar_shading_authoritative
        )
        self._all_non_working_intervals = tuple(
            (interval.start_day_ordinal, interval.finish_day_ordinal)
            for interval in (projection.non_working_intervals if projection else ())
        )
        self._refresh_effective_base_range()
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)

    def set_baseline_overlay(self, overlay: GanttBaselineOverlayDto | None) -> None:
        if overlay is not None and overlay.project_id != self._projection_project_id:
            raise ValueError("The Gantt baseline overlay belongs to another project.")
        start = overlay.range_start_day_ordinal if overlay else None
        finish = overlay.range_finish_day_ordinal if overlay else None
        self._baseline_start_day = int(start) if start is not None else -1
        self._baseline_finish_day = int(finish) if finish is not None else -1
        self._refresh_effective_base_range()
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)

    @Slot(str, result=bool)
    def setTimescale(self, timescale: str) -> bool:
        normalized = str(timescale or "").strip().lower()
        if normalized not in _TIMESCALE_BASE_DENSITY:
            return False
        if normalized == self._timescale and self._zoom_index == _NEUTRAL_ZOOM_INDEX:
            return True
        self._timescale = normalized
        self._zoom_index = _NEUTRAL_ZOOM_INDEX
        self._rebuild_range()
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)
        return True

    @Slot(str, float, result=bool)
    def restoreConfiguration(self, timescale: str, zoom_multiplier: float) -> bool:
        normalized_timescale = str(timescale or "").strip().lower()
        if normalized_timescale not in _TIMESCALE_BASE_DENSITY:
            normalized_timescale = "week"
        try:
            zoom_index = next(
                index
                for index, level in enumerate(_ZOOM_LEVELS)
                if abs(level - float(zoom_multiplier)) < 0.000_001
            )
        except (StopIteration, TypeError, ValueError):
            zoom_index = _NEUTRAL_ZOOM_INDEX
        if (
            normalized_timescale == self._timescale
            and zoom_index == self._zoom_index
        ):
            return True
        self._timescale = normalized_timescale
        self._zoom_index = zoom_index
        self._rebuild_range()
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)
        return True

    @Slot(result=bool)
    def zoomIn(self) -> bool:
        if not self.canZoomIn:
            return False
        self._zoom_index += 1
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)
        return True

    @Slot(result=bool)
    def zoomOut(self) -> bool:
        if not self.canZoomOut:
            return False
        self._zoom_index -= 1
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)
        return True

    @Slot(result=bool)
    def resetZoom(self) -> bool:
        if not self.hasRange:
            return False
        if self._zoom_index == _NEUTRAL_ZOOM_INDEX:
            return True
        self._zoom_index = _NEUTRAL_ZOOM_INDEX
        self.configurationChanged.emit()
        self._rebuild_viewport(force=True)
        return True

    @Slot(float, float)
    def updateViewport(self, content_x: float, viewport_width: float) -> None:
        normalized_width = max(0.0, float(viewport_width))
        max_content_x = max(0.0, self.contentWidth - normalized_width)
        normalized_x = min(max(0.0, float(content_x)), max_content_x)
        if (
            abs(normalized_x - self._viewport_content_x) < 0.01
            and abs(normalized_width - self._viewport_width) < 0.01
        ):
            return
        self._viewport_content_x = normalized_x
        self._viewport_width = normalized_width
        self._rebuild_viewport()

    def _rebuild_range(self) -> None:
        if self._base_start_day < 1 or self._base_finish_day < self._base_start_day:
            self._range_start_day = -1
            self._range_finish_day = -1
            return
        start = date.fromordinal(self._base_start_day)
        finish = date.fromordinal(self._base_finish_day)
        if self._timescale == "day":
            start -= timedelta(days=3)
            finish += timedelta(days=3)
        elif self._timescale == "week":
            start -= timedelta(days=7)
            finish += timedelta(days=7)
        elif self._timescale == "month":
            start = _add_months(start, -1)
            finish = _add_months(finish, 1)
        else:
            start = _add_months(start, -3)
            finish = _add_months(finish, 3)
        self._range_start_day = start.toordinal()
        self._range_finish_day = finish.toordinal()

    def _refresh_effective_base_range(self) -> None:
        starts = [
            value
            for value in (self._projection_start_day, self._baseline_start_day)
            if value > 0
        ]
        finishes = [
            value
            for value in (self._projection_finish_day, self._baseline_finish_day)
            if value > 0
        ]
        self._base_start_day = min(starts) if starts else -1
        self._base_finish_day = max(finishes) if finishes else -1
        self._rebuild_range()

    def _rebuild_viewport(self, *, force: bool = False) -> None:
        previous = (
            self._visible_start_day,
            self._visible_finish_day,
            self._major_ticks,
            self._minor_ticks,
            self._visible_non_working_intervals,
        )
        if not self.hasRange:
            self._viewport_content_x = 0.0
            self._visible_start_day = -1
            self._visible_finish_day = -1
            self._major_ticks = []
            self._minor_ticks = []
            self._visible_non_working_intervals = []
        else:
            density = self.pixelsPerDay
            max_content_x = max(0.0, self.contentWidth - self._viewport_width)
            self._viewport_content_x = min(
                max(0.0, self._viewport_content_x), max_content_x
            )
            self._visible_start_day = min(
                self._range_finish_day,
                self._range_start_day + floor(self._viewport_content_x / density),
            )
            visible_days = max(1, ceil(self._viewport_width / density))
            self._visible_finish_day = min(
                self._range_finish_day,
                self._visible_start_day + visible_days - 1,
            )
            window_start, window_finish = self._descriptor_window()
            self._major_ticks, self._minor_ticks = _build_ticks(
                self._timescale,
                range_start=self._range_start_day,
                range_finish=self._range_finish_day,
                window_start=window_start,
                window_finish=window_finish,
            )
            self._visible_non_working_intervals = [
                {
                    "startDay": max(start, window_start, self._range_start_day),
                    "finishDay": min(finish, window_finish, self._range_finish_day),
                }
                for start, finish in self._all_non_working_intervals
                if finish >= window_start and start <= window_finish
            ]
        current = (
            self._visible_start_day,
            self._visible_finish_day,
            self._major_ticks,
            self._minor_ticks,
            self._visible_non_working_intervals,
        )
        if force or current != previous:
            self.viewportChanged.emit()

    def _descriptor_window(self) -> tuple[int, int]:
        buffer_days = {"day": 7, "week": 14, "month": 62, "quarter": 186}[
            self._timescale
        ]
        return (
            max(self._range_start_day, self._visible_start_day - buffer_days),
            min(self._range_finish_day, self._visible_finish_day + buffer_days),
        )


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _build_ticks(
    timescale: str,
    *,
    range_start: int,
    range_finish: int,
    window_start: int,
    window_finish: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start = date.fromordinal(window_start)
    finish = date.fromordinal(window_finish)
    if timescale in {"day", "week"}:
        major = _calendar_intervals(
            _month_start(start), finish, _next_month, lambda value: value.strftime("%B %Y")
        )
    else:
        major = _calendar_intervals(
            date(start.year, 1, 1), finish, _next_year, lambda value: str(value.year)
        )
    if timescale == "day":
        minor = [
            (value, value, str(value.day))
            for value in _date_values(start, finish)
        ]
    elif timescale == "week":
        week_start = start - timedelta(days=start.weekday())
        minor = _calendar_intervals(
            week_start,
            finish,
            lambda value: value + timedelta(days=7),
            lambda value: f"W{value.isocalendar().week:02d}",
        )
    elif timescale == "month":
        minor = _calendar_intervals(
            _month_start(start), finish, _next_month, lambda value: value.strftime("%b")
        )
    else:
        minor = _calendar_intervals(
            _quarter_start(start), finish, _next_quarter, _quarter_label
        )
    return (
        _serialize_ticks(major, "major", range_start, range_finish, window_start, window_finish),
        _serialize_ticks(minor, "minor", range_start, range_finish, window_start, window_finish),
    )


def _calendar_intervals(
    start: date,
    finish: date,
    advance: Callable[[date], date],
    label: Callable[[date], str],
) -> list[tuple[date, date, str]]:
    result: list[tuple[date, date, str]] = []
    cursor = start
    while cursor <= finish:
        next_cursor = advance(cursor)
        result.append((cursor, next_cursor - timedelta(days=1), label(cursor)))
        cursor = next_cursor
    return result


def _serialize_ticks(
    ticks: Iterable[tuple[date, date, str]],
    kind: str,
    range_start: int,
    range_finish: int,
    window_start: int,
    window_finish: int,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for start, finish, label in ticks:
        start_day = max(start.toordinal(), range_start)
        finish_day = min(finish.toordinal(), range_finish)
        if finish_day < window_start or start_day > window_finish:
            continue
        result.append(
            {
                "startDay": start_day,
                "finishDay": finish_day,
                "label": label,
                "kind": kind,
            }
        )
    return result


def _date_values(start: date, finish: date) -> Iterable[date]:
    cursor = start
    while cursor <= finish:
        yield cursor
        cursor += timedelta(days=1)


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    return _add_months(value, 1)


def _next_year(value: date) -> date:
    return date(value.year + 1, 1, 1)


def _quarter_start(value: date) -> date:
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def _next_quarter(value: date) -> date:
    return _add_months(value, 3)


def _quarter_label(value: date) -> str:
    return f"Q{((value.month - 1) // 3) + 1}"


__all__ = ["GanttTimeAxisController"]
