from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from src.ui_qml.platform.presenters.calendars.calendar_catalog_presenter import (
    PlatformCalendarCatalogPresenter,
)


@dataclass
class _FakeResult:
    ok: bool = True
    data: object = None
    error: object = None


def _calendar(**overrides) -> SimpleNamespace:
    base = dict(
        id="cal-1",
        organization_id="org-1",
        name="Global Calendar",
        description="",
        code="GLOBAL",
        calendar_type="GLOBAL",
        timezone="Europe/Berlin",
        is_default=True,
        is_active=True,
        effective_from="",
        effective_to="",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _rule(weekday: int, is_working_day: bool) -> SimpleNamespace:
    return SimpleNamespace(weekday=weekday, is_working_day=is_working_day)


class _FakeCalendarApi:
    def __init__(self, calendars, *, working_rules=(), assignments=None):
        self._calendars = calendars
        self._working_rules = working_rules
        self._assignments = assignments or {}

    def list_calendars(self):
        return _FakeResult(data=self._calendars)

    def list_working_rules(self, calendar_id):
        return _FakeResult(data=self._working_rules)

    def list_calendar_assignments(self, calendar_id):
        return _FakeResult(data=self._assignments)


def test_serialize_calendar_status_label_reflects_active_state_not_calendar_type():
    api = _FakeCalendarApi([_calendar(is_active=True), _calendar(id="cal-2", is_active=False)])
    presenter = PlatformCalendarCatalogPresenter(platform_calendar_api=api)

    catalog = presenter.build_catalog()

    assert catalog.items[0].status_label == {"label": "Active", "tone": "success"}
    assert catalog.items[1].status_label == {"label": "Inactive", "tone": "neutral"}


def test_serialize_calendar_subtitle_is_a_working_week_label_not_code_and_timezone():
    rules = [_rule(d, True) for d in range(5)] + [_rule(5, False), _rule(6, False)]
    api = _FakeCalendarApi([_calendar()], working_rules=rules)
    presenter = PlatformCalendarCatalogPresenter(platform_calendar_api=api)

    catalog = presenter.build_catalog()

    assert catalog.items[0].subtitle == "Mon–Fri"
    assert catalog.items[0].state["workingWeekLabel"] == "Mon–Fri"
    assert catalog.items[0].state["code"] == "GLOBAL"
    assert catalog.items[0].state["timeZone"] == "Europe/Berlin"


def test_serialize_calendar_type_label_is_human_readable():
    api = _FakeCalendarApi([_calendar(calendar_type="DEPARTMENT")])
    presenter = PlatformCalendarCatalogPresenter(platform_calendar_api=api)

    catalog = presenter.build_catalog()

    assert catalog.items[0].state["typeLabel"] == "Department"
    assert "Department" in catalog.items[0].supporting_text


def test_serialize_calendar_usage_label_counts_across_all_assignment_groups():
    api = _FakeCalendarApi(
        [_calendar()],
        assignments={
            "sites": (object(), object()),
            "departments": (object(),),
            "employees": (),
            "projects": (),
            "resources": (),
        },
    )
    presenter = PlatformCalendarCatalogPresenter(platform_calendar_api=api)

    catalog = presenter.build_catalog()

    assert catalog.items[0].meta_text == "3 assignments"
    assert catalog.items[0].state["usageCount"] == 3


def test_serialize_calendar_usage_label_handles_zero_assignments():
    api = _FakeCalendarApi([_calendar()], assignments={})
    presenter = PlatformCalendarCatalogPresenter(platform_calendar_api=api)

    catalog = presenter.build_catalog()

    assert catalog.items[0].meta_text == "No assignments"
    assert catalog.items[0].state["usageCount"] == 0
