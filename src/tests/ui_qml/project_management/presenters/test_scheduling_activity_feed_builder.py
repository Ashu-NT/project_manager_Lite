from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.scheduling.activity_feed_builder import (
    build_activity_feed_collection,
)


def _delayed(**overrides) -> SimpleNamespace:
    fields = dict(task_id="task-1", name="Cable Pull", late_by_days=3, finish_date=None)
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _resource_load(**overrides) -> SimpleNamespace:
    fields = dict(
        resource_id="res-1",
        resource_name="Ada",
        utilization_percent=120.0,
        utilization_label="120%",
        tasks_count=5,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_log_entries_map_status_label_to_an_explicit_tone() -> None:
    result = build_activity_feed_collection(
        schedule_items=(),
        delayed_items=(),
        resource_load=(),
        activity_log=({"title": "Recalculated schedule", "statusLabel": "Info", "subtitle": "", "metaText": "Just now"},),
    )

    item = result["items"][0]
    assert item["tone"] == "info"
    assert item["badgeLabel"] == "Info"
    assert item["occurredAtLabel"] == "Just now"


def test_unrecognized_status_label_falls_back_to_neutral_tone() -> None:
    result = build_activity_feed_collection(
        schedule_items=(),
        delayed_items=(),
        resource_load=(),
        activity_log=({"title": "Custom event", "statusLabel": "Unusual", "subtitle": "", "metaText": ""},),
    )

    assert result["items"][0]["tone"] == "neutral"


def test_top_delayed_task_gets_a_warning_tone_row() -> None:
    result = build_activity_feed_collection(
        schedule_items=(),
        delayed_items=(_delayed(),),
        resource_load=(),
        activity_log=(),
    )

    item = result["items"][0]
    assert item["title"] == "Cable Pull is late"
    assert item["tone"] == "warning"
    assert item["badgeLabel"] == "Warning"


def test_overloaded_resource_gets_a_danger_tone_row() -> None:
    result = build_activity_feed_collection(
        schedule_items=(),
        delayed_items=(),
        resource_load=(_resource_load(),),
        activity_log=(),
    )

    item = result["items"][0]
    assert item["title"] == "Ada exceeds capacity"
    assert item["tone"] == "danger"
    assert item["badgeLabel"] == "Danger"


def test_does_not_fabricate_actor_or_raw_timestamp_data() -> None:
    result = build_activity_feed_collection(
        schedule_items=(),
        delayed_items=(_delayed(),),
        resource_load=(),
        activity_log=(),
    )

    item = result["items"][0]
    assert item["actorDisplay"] == "System"
    assert item["occurredAt"] is None
