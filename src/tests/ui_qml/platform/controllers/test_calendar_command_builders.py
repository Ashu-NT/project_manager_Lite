from __future__ import annotations

from src.ui_qml.platform.controllers.calendars.command_builders import (
    build_calendar_update_command,
    build_exception_update_command,
    build_recurring_event_update_command,
)


def test_update_command_omits_is_active_when_not_present_in_payload():
    """A plain profile-field edit (name/timezone/description) must not
    accidentally deactivate the calendar -- is_active stays None (untouched)
    unless the caller explicitly includes isActive in the payload."""
    command = build_calendar_update_command({"calendarId": "cal-1", "name": "New Name"})

    assert command.is_active is None


def test_update_command_maps_is_active_true_for_an_activate_action():
    command = build_calendar_update_command({"calendarId": "cal-1", "isActive": True})

    assert command.is_active is True


def test_update_command_maps_is_active_false_for_a_deactivate_action():
    command = build_calendar_update_command({"calendarId": "cal-1", "isActive": False})

    assert command.is_active is False


def test_update_command_maps_effective_from_and_to():
    command = build_calendar_update_command({
        "calendarId": "cal-1",
        "effectiveFrom": "2026-01-01",
        "effectiveTo": "2026-12-31",
    })

    assert command.effective_from == "2026-01-01"
    assert command.effective_to == "2026-12-31"


def test_exception_update_command_omits_priority_when_not_present():
    command = build_exception_update_command({"exceptionId": "exc-1", "name": "New Name"})

    assert command.priority is None


def test_exception_update_command_maps_fields():
    command = build_exception_update_command({
        "exceptionId": "exc-1",
        "name": "Training Day",
        "exceptionType": "TRAINING",
        "impactType": "REDUCED_CAPACITY",
        "hoursOverride": 4.0,
        "priority": 5,
        "approvalStatus": "APPROVED",
    })

    assert command.exception_id == "exc-1"
    assert command.name == "Training Day"
    assert command.exception_type == "TRAINING"
    assert command.impact_type == "REDUCED_CAPACITY"
    assert command.hours_override == 4.0
    assert command.priority == 5
    assert command.approval_status == "APPROVED"


def test_recurring_event_update_command_omits_is_active_when_not_present():
    command = build_recurring_event_update_command({"eventId": "evt-1", "title": "New Title"})

    assert command.is_active is None


def test_recurring_event_update_command_maps_is_active_for_deactivate():
    command = build_recurring_event_update_command({"eventId": "evt-1", "isActive": False})

    assert command.is_active is False


def test_recurring_event_update_command_maps_fields():
    command = build_recurring_event_update_command({
        "eventId": "evt-1",
        "title": "Weekly Standup",
        "eventType": "MEETING",
        "recurrenceRule": "FREQ=WEEKLY;BYDAY=MO",
        "startTime": "09:00",
        "endTime": "09:30",
        "impactType": "REDUCED_CAPACITY",
        "effectiveFrom": "2026-10-07",
        "effectiveTo": "2027-10-07",
    })

    assert command.event_id == "evt-1"
    assert command.title == "Weekly Standup"
    assert command.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO"
    assert command.effective_from == "2026-10-07"
    assert command.effective_to == "2027-10-07"
