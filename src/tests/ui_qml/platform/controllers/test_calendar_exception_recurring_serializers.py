"""Exceptions/Recurring table row + Inspector read projections -- both the
table and the Inspector read the same serialized object, and raw backend
enum values (TRAINING, REDUCED_CAPACITY, ...) must never leak through as
display text."""

from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.platform.controllers.calendars.serializers import (
    serialize_calendar_exception,
    serialize_recurring_event,
)


@dataclass
class _FakeException:
    id: str = "exc-1"
    exception_date: str = "2026-10-20"
    exception_type: str = "TRAINING"
    name: str = "Training Day"
    impact_type: str = "REDUCED_CAPACITY"
    approval_status: str = "APPROVED"
    description: str = "Team-wide training session"
    start_time: str = "08:00"
    end_time: str = "12:00"
    hours_override: float = 4.0


@dataclass
class _FakeRecurringEvent:
    id: str = "evt-1"
    title: str = "Weekly Standup"
    event_type: str = "MEETING"
    recurrence_rule: str = "FREQ=WEEKLY;BYDAY=MO"
    impact_type: str = "REDUCED_CAPACITY"
    is_active: bool = True
    start_time: str = "10:00"
    end_time: str = "11:00"
    effective_from: str = "2026-10-07"
    effective_to: str = "2027-10-07"
    capacity_impact_percent: float = 0.0


def test_exception_humanizes_type_impact_and_status_labels():
    view = serialize_calendar_exception(_FakeException())

    assert view["typeLabel"] == "Training"
    assert view["impactLabel"] == "Reduced Capacity"
    assert view["statusLabel"] == "Approved"
    assert "_" not in view["typeLabel"]
    assert "_" not in view["impactLabel"]


def test_exception_site_closed_humanizes_as_two_words():
    view = serialize_calendar_exception(_FakeException(exception_type="SITE_CLOSED", impact_type="UNAVAILABLE"))

    assert view["typeLabel"] == "Site Closed"
    assert view["impactLabel"] == "Unavailable"


def test_exception_date_label_is_formatted_for_display():
    view = serialize_calendar_exception(_FakeException())

    assert view["dateLabel"] == "20 Oct 2026"


def test_exception_carries_working_time_and_description_for_inspector():
    view = serialize_calendar_exception(_FakeException())

    assert view["startTimeLabel"] == "08:00"
    assert view["endTimeLabel"] == "12:00"
    assert view["hoursOverride"] == 4.0
    assert view["description"] == "Team-wide training session"


def test_exception_with_no_description_is_an_empty_string_not_none():
    view = serialize_calendar_exception(_FakeException(description=""))

    assert view["description"] == ""


def test_recurring_event_recurrence_label_is_human_readable_not_raw_rrule():
    view = serialize_recurring_event(_FakeRecurringEvent())

    assert view["recurrenceLabel"] == "Every Monday"
    assert view["recurrenceRule"] == "FREQ=WEEKLY;BYDAY=MO"  # raw rule still available for Advanced display


def test_recurring_event_humanizes_type_and_impact_labels():
    view = serialize_recurring_event(_FakeRecurringEvent())

    assert view["typeLabel"] == "Meeting"
    assert view["impactLabel"] == "Reduced Capacity"


def test_recurring_event_status_label_reflects_is_active():
    active = serialize_recurring_event(_FakeRecurringEvent(is_active=True))
    inactive = serialize_recurring_event(_FakeRecurringEvent(is_active=False))

    assert active["statusLabel"] == "Active"
    assert inactive["statusLabel"] == "Inactive"


def test_recurring_event_effective_dates_are_formatted_for_display():
    view = serialize_recurring_event(_FakeRecurringEvent())

    assert view["effectiveFromLabel"] == "07 Oct 2026"
    assert view["effectiveToLabel"] == "07 Oct 2027"


def test_recurring_event_with_no_end_date_has_empty_label_not_a_placeholder():
    view = serialize_recurring_event(_FakeRecurringEvent(effective_to=""))

    assert view["effectiveTo"] == ""
    assert view["effectiveToLabel"] == ""


def test_exception_status_chip_tones_use_shared_status_chip_vocabulary():
    approved = serialize_calendar_exception(_FakeException(approval_status="APPROVED"))
    pending = serialize_calendar_exception(_FakeException(approval_status="PENDING"))
    rejected = serialize_calendar_exception(_FakeException(approval_status="REJECTED"))

    assert approved["statusTone"] == "success"
    assert pending["statusTone"] == "warning"
    assert rejected["statusTone"] == "danger"


def test_exception_impact_tone_uses_shared_status_chip_vocabulary():
    view = serialize_calendar_exception(_FakeException(impact_type="UNAVAILABLE"))

    assert view["impactTone"] == "danger"


def test_recurring_event_status_tone_reflects_active_state():
    active = serialize_recurring_event(_FakeRecurringEvent(is_active=True))
    inactive = serialize_recurring_event(_FakeRecurringEvent(is_active=False))

    assert active["statusTone"] == "success"
    assert inactive["statusTone"] == "neutral"
