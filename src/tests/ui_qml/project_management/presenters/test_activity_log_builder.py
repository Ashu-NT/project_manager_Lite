from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
    humanize_action,
    icon_key_for_entity_type,
    tone_for_action,
)


def _entry(**overrides):
    fields = dict(
        id="e1",
        action="project.create",
        entity_type="project",
        actor_id="u1",
        summary="",
        details={},
        occurred_at=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_tone_for_action_classifies_by_verb_not_status_text() -> None:
    assert tone_for_action("project.create") == "success"
    assert tone_for_action("project.delete") == "danger"
    assert tone_for_action("project.update") == "warning"
    assert tone_for_action("task.list") == "neutral"
    assert tone_for_action("") == "neutral"


def test_icon_key_for_entity_type_uses_registered_keys_with_a_fallback() -> None:
    assert icon_key_for_entity_type("employee") == "employee"
    assert icon_key_for_entity_type("task") == "tasks"
    assert icon_key_for_entity_type("PROJECT") == "project"
    assert icon_key_for_entity_type("some_future_entity") == "history"
    assert icon_key_for_entity_type("") == "history"


def test_humanize_action_produces_a_readable_fallback_title() -> None:
    assert humanize_action("project.create") == "Project Create"
    assert humanize_action("task.set_status") == "Task Set Status"
    assert humanize_action("") == ""


def test_build_activity_records_produces_the_canonical_shape() -> None:
    entry = _entry(summary="Project created — Apollo")
    actor_lookup = {"u1": "Ada Lovelace"}
    records = build_activity_records(
        [entry],
        actor_lookup=actor_lookup,
        field_labels={},
    )
    assert len(records) == 1
    record = records[0]
    assert record.id == "e1"
    assert record.title == "Project created — Apollo"
    assert record.actor_display == "Ada Lovelace"
    assert record.occurred_at == entry.occurred_at
    assert record.occurred_at_label == "05 Mar 2026 14:30"
    assert record.icon_key == "project"
    assert record.tone == "success"


def test_build_activity_records_falls_back_to_humanized_action_when_no_summary() -> None:
    entry = _entry(summary="", action="task.set_status", entity_type="task")
    records = build_activity_records([entry], actor_lookup={}, field_labels={})
    assert records[0].title == "Task Set Status"


def test_build_activity_records_falls_back_to_humanized_action_when_summary_equals_action() -> None:
    entry = _entry(summary="task.set_status", action="task.set_status", entity_type="task")
    records = build_activity_records([entry], actor_lookup={}, field_labels={})
    assert records[0].title == "Task Set Status"


def test_build_activity_records_falls_back_to_system_for_unknown_actor() -> None:
    entry = _entry(actor_id=None)
    records = build_activity_records([entry], actor_lookup={}, field_labels={})
    assert records[0].actor_display == "System"


def test_build_activity_records_builds_supporting_text_from_changes() -> None:
    entry = _entry(
        details={"changes": {"status": {"from": "draft", "to": "active"}}},
    )
    records = build_activity_records(
        [entry],
        actor_lookup={},
        field_labels={"status": "Status"},
    )
    assert records[0].supporting_text == "Status: Draft → Active"
