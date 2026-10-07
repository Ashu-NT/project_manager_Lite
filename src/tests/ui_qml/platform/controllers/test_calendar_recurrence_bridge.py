"""QML-facing recurrence bridge -- thin adaptation only; the actual
translation logic is covered by test_recurrence_text.py."""

from __future__ import annotations

from src.ui_qml.platform.controllers.calendars.recurrence import (
    build_recurrence_rule,
    default_recurrence_editor_state,
    parse_recurrence_rule,
    recurrence_summary,
)


def test_recurrence_summary_formats_for_qml():
    assert recurrence_summary("FREQ=WEEKLY;BYDAY=MO") == "Every Monday"


def test_recurrence_summary_uses_effective_from_for_yearly():
    assert recurrence_summary("FREQ=YEARLY", "2026-10-07") == "Every year on 7 October"


def test_recurrence_summary_tolerates_malformed_effective_from():
    assert recurrence_summary("FREQ=YEARLY", "not-a-date") == "Every year"


def test_build_recurrence_rule_success():
    result = build_recurrence_rule({"frequency": "WEEKLY", "interval": 1, "byDay": ["MO"]})
    assert result == {"ok": True, "rrule": "FREQ=WEEKLY;BYDAY=MO", "errorMessage": ""}


def test_build_recurrence_rule_validation_error_surfaces_as_ok_false():
    result = build_recurrence_rule({"frequency": "WEEKLY", "interval": 1, "byDay": []})
    assert result["ok"] is False
    assert "at least one selected day" in result["errorMessage"]


def test_parse_recurrence_rule_known_shape():
    result = parse_recurrence_rule("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR")
    assert result["ok"] is True
    assert result["frequency"] == "EVERY_WEEKDAY"


def test_parse_recurrence_rule_unknown_shape_returns_ok_false():
    assert parse_recurrence_rule("FREQ=WEEKLY;BYWEEKNO=3;BYDAY=MO") == {"ok": False}


def test_default_recurrence_editor_state_is_a_plain_dict():
    state = default_recurrence_editor_state()
    assert state["frequency"] == "WEEKLY"
    assert isinstance(state, dict)
