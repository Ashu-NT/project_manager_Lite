from __future__ import annotations

from src.ui_qml.platform.controllers.calendars.command_builders import (
    build_calendar_update_command,
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
