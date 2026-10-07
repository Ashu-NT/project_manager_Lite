"""Recurrence editor state <-> RRULE translation, and RRULE -> human text.

RFC5545 RRULE remains the canonical persisted/executed format (see
WorkingTimeCalculator.recurring_event_occurs_on) -- this module only covers
the presentation/translation layer the visual recurrence editor and the
Exceptions/Recurring tables read."""

from __future__ import annotations

from datetime import date

import pytest

from src.core.platform.application.time_management.calendar.definitions.recurrence_text import (
    build_rrule_from_editor_state,
    humanize_rrule,
    parse_rrule_to_editor_state,
)


def test_daily_every_day():
    state = {"frequency": "DAILY", "interval": 1}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=DAILY"
    assert humanize_rrule(rrule) == "Daily"


def test_daily_every_n_days():
    state = {"frequency": "DAILY", "interval": 3}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=DAILY;INTERVAL=3"
    assert humanize_rrule(rrule) == "Every 3 days"


def test_every_weekday_preset():
    state = {"frequency": "EVERY_WEEKDAY"}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    assert humanize_rrule(rrule) == "Every weekday"


def test_weekly_one_day():
    state = {"frequency": "WEEKLY", "interval": 1, "byDay": ["MO"]}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=WEEKLY;BYDAY=MO"
    assert humanize_rrule(rrule) == "Every Monday"


def test_weekly_multiple_days():
    state = {"frequency": "WEEKLY", "interval": 1, "byDay": ["WE", "MO"]}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=WEEKLY;BYDAY=MO,WE"  # always normalized to calendar order
    assert humanize_rrule(rrule) == "Weekly on Monday and Wednesday"


def test_every_n_weeks_multiple_days():
    state = {"frequency": "WEEKLY", "interval": 2, "byDay": ["MO", "WE"]}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE"
    assert humanize_rrule(rrule) == "Every 2 weeks on Monday and Wednesday"


def test_weekly_requires_at_least_one_day():
    with pytest.raises(ValueError, match="at least one selected day"):
        build_rrule_from_editor_state({"frequency": "WEEKLY", "interval": 1, "byDay": []})


def test_monthly_on_day_of_month():
    state = {"frequency": "MONTHLY", "interval": 1, "monthlyMode": "DAY_OF_MONTH", "dayOfMonth": 7}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=MONTHLY;BYMONTHDAY=7"
    assert humanize_rrule(rrule) == "Monthly on day 7"


def test_monthly_every_n_months_on_day_of_month():
    state = {"frequency": "MONTHLY", "interval": 3, "monthlyMode": "DAY_OF_MONTH", "dayOfMonth": 1}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=1"
    assert humanize_rrule(rrule) == "Every 3 months on day 1"


def test_monthly_on_nth_weekday():
    state = {
        "frequency": "MONTHLY", "interval": 1, "monthlyMode": "NTH_WEEKDAY",
        "nth": 1, "nthWeekday": "MO",
    }
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1"
    assert humanize_rrule(rrule) == "Monthly on the first Monday"


def test_monthly_on_last_weekday():
    state = {
        "frequency": "MONTHLY", "interval": 1, "monthlyMode": "NTH_WEEKDAY",
        "nth": -1, "nthWeekday": "FR",
    }
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1"
    assert humanize_rrule(rrule) == "Monthly on the last Friday"


def test_yearly():
    state = {"frequency": "YEARLY", "interval": 1}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=YEARLY"
    assert humanize_rrule(rrule, effective_from=date(2026, 10, 7)) == "Every year on 7 October"


def test_yearly_every_n_years():
    state = {"frequency": "YEARLY", "interval": 2}
    rrule = build_rrule_from_editor_state(state)
    assert rrule == "FREQ=YEARLY;INTERVAL=2"
    assert humanize_rrule(rrule, effective_from=date(2026, 12, 25)) == "Every 2 years on 25 December"


def test_yearly_without_effective_from_omits_date():
    assert humanize_rrule("FREQ=YEARLY") == "Every year"


def test_existing_rrule_loads_correctly_into_editor_state_for_edit():
    state = parse_rrule_to_editor_state("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR")
    assert state["frequency"] == "EVERY_WEEKDAY"

    state = parse_rrule_to_editor_state("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE")
    assert state["frequency"] == "WEEKLY"
    assert state["interval"] == 2
    assert state["byDay"] == ["MO", "WE"]

    state = parse_rrule_to_editor_state("FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1")
    assert state["frequency"] == "MONTHLY"
    assert state["monthlyMode"] == "NTH_WEEKDAY"
    assert state["nth"] == -1
    assert state["nthWeekday"] == "FR"


def test_unrecognized_rrule_shape_falls_back_to_none_not_a_guess():
    # BYWEEKNO is a real RFC5545 part this editor doesn't expose -- must not
    # be silently approximated or dropped.
    assert parse_rrule_to_editor_state("FREQ=WEEKLY;BYWEEKNO=3;BYDAY=MO") is None
    assert parse_rrule_to_editor_state("") is None
    assert parse_rrule_to_editor_state("NOT;A=RULE") is None


def test_unrecognized_rrule_humanizes_to_the_raw_string_not_hidden():
    raw = "FREQ=WEEKLY;BYWEEKNO=3;BYDAY=MO"
    assert humanize_rrule(raw) == raw


def test_round_trip_every_supported_shape_preserves_meaning():
    shapes = [
        {"frequency": "DAILY", "interval": 1},
        {"frequency": "DAILY", "interval": 5},
        {"frequency": "EVERY_WEEKDAY"},
        {"frequency": "WEEKLY", "interval": 1, "byDay": ["MO"]},
        {"frequency": "WEEKLY", "interval": 2, "byDay": ["MO", "WE", "FR"]},
        {"frequency": "MONTHLY", "interval": 1, "monthlyMode": "DAY_OF_MONTH", "dayOfMonth": 15},
        {"frequency": "MONTHLY", "interval": 2, "monthlyMode": "NTH_WEEKDAY", "nth": 2, "nthWeekday": "TU"},
        {"frequency": "YEARLY", "interval": 1},
    ]
    for state in shapes:
        rrule = build_rrule_from_editor_state(state)
        round_tripped = parse_rrule_to_editor_state(rrule)
        assert round_tripped is not None, rrule
        assert build_rrule_from_editor_state(round_tripped) == rrule
