from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.portfolio.action_mapper import (
    to_recent_action_activity_item,
)


def _recent_action(**overrides) -> SimpleNamespace:
    fields = dict(
        occurred_at_label="2026-03-05 14:30",
        project_name="Project Apollo",
        actor_username="ada",
        action_label="Project Updated",
        summary="Budget line adjusted.",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_project_name_is_carried_as_subject_display_not_status_label() -> None:
    item = to_recent_action_activity_item(_recent_action())

    assert item.subject_display == "Project Apollo"
    assert item.status_label == ""


def test_maps_title_description_actor_and_timestamp_label() -> None:
    item = to_recent_action_activity_item(_recent_action())

    assert item.title == "Project Updated"
    assert item.description == "Budget line adjusted."
    assert item.actor_display == "ada"
    assert item.occurred_at_label == "2026-03-05 14:30"


def test_falls_back_to_system_when_actor_username_is_missing() -> None:
    item = to_recent_action_activity_item(_recent_action(actor_username=""))

    assert item.actor_display == "System"
