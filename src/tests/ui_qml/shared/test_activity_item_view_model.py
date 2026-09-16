from __future__ import annotations

from datetime import datetime, timezone

from src.ui_qml.shared.models.activity_item import (
    VALID_TONES,
    ActivityItemViewModel,
    serialize_activity_item,
    serialize_activity_items,
)


def _item(**overrides) -> ActivityItemViewModel:
    fields = dict(id="a1", title="Project created")
    fields.update(overrides)
    return ActivityItemViewModel(**fields)


def test_title_means_event_headline_not_actor() -> None:
    """title and actor_display are independent fields; title never holds
    the actor's name."""
    item = _item(title="Project created", actor_display="Ada Lovelace")
    payload = serialize_activity_item(item)
    assert payload["title"] == "Project created"
    assert payload["actorDisplay"] == "Ada Lovelace"
    assert payload["title"] != payload["actorDisplay"]


def test_actor_defaults_to_system_when_unspecified() -> None:
    item = _item()
    assert item.actor_display == "System"
    assert serialize_activity_item(item)["actorDisplay"] == "System"


def test_explicit_tone_is_preserved_for_every_valid_value() -> None:
    for tone in VALID_TONES:
        item = _item(tone=tone)
        assert item.tone == tone
        assert serialize_activity_item(item)["tone"] == tone


def test_invalid_tone_fails_safe_to_neutral_regardless_of_text_content() -> None:
    """Changing title/description/badge_label text must never change the
    resolved tone -- only an explicit, valid tone value can."""
    item_a = _item(title="Catastrophic failure", description="Everything broke", badge_label="Failed", tone="not-a-real-tone")
    item_b = _item(title="Routine update", description="Nothing happened", badge_label="", tone="not-a-real-tone")
    assert item_a.tone == item_b.tone == "neutral"

    item_c = _item(title="Approved", badge_label="Approved", tone="danger")
    item_d = _item(title="Approved", badge_label="Approved", tone="success")
    assert item_c.tone == "danger"
    assert item_d.tone == "success"


def test_badge_label_is_optional_and_empty_by_default() -> None:
    item = _item()
    assert item.badge_label == ""
    assert serialize_activity_item(item)["badgeLabel"] == ""


def test_badge_label_can_carry_a_real_outcome_when_supplied() -> None:
    item = _item(badge_label="Rejected", tone="danger")
    assert serialize_activity_item(item)["badgeLabel"] == "Rejected"


def test_raw_and_formatted_timestamp_are_both_available_independently() -> None:
    when = datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc)
    item = _item(occurred_at=when, occurred_at_label="05 Mar 2026, 14:30")
    payload = serialize_activity_item(item)
    assert payload["occurredAt"] == when.isoformat()
    assert payload["occurredAtLabel"] == "05 Mar 2026, 14:30"
    # The two are independent -- the raw value round-trips regardless of
    # whatever display format the presenter chose for the label.
    assert payload["occurredAt"] != payload["occurredAtLabel"]


def test_missing_occurred_at_serializes_to_none_not_a_placeholder_string() -> None:
    item = _item(occurred_at=None, occurred_at_label="")
    payload = serialize_activity_item(item)
    assert payload["occurredAt"] is None
    assert payload["occurredAtLabel"] == ""


def test_supporting_text_carries_optional_diff_or_change_summary() -> None:
    item = _item(supporting_text="Status: Draft → Approved")
    assert serialize_activity_item(item)["supportingText"] == "Status: Draft → Approved"
    assert _item().supporting_text == ""


def test_subject_display_carries_an_optional_related_object_label() -> None:
    item = _item(subject_display="Project Apollo")
    assert serialize_activity_item(item)["subjectDisplay"] == "Project Apollo"
    assert _item().subject_display == ""


def test_activation_state_none_means_not_independently_clickable() -> None:
    item = _item(activation_state=None)
    assert serialize_activity_item(item)["activationState"] is None


def test_activation_state_present_carries_an_opaque_navigation_payload() -> None:
    payload_in = {"routeId": "project_management.tasks", "taskId": "t1"}
    item = _item(activation_state=payload_in)
    payload_out = serialize_activity_item(item)
    assert payload_out["activationState"] == payload_in
    # The view model doesn't interpret the payload -- any shape survives untouched.
    other_shape = {"targetScreen": "portfolio", "projectId": "p1", "nested": {"a": 1}}
    assert serialize_activity_item(_item(activation_state=other_shape))["activationState"] == other_shape


def test_serialize_activity_items_maps_a_sequence_in_order() -> None:
    items = [_item(id="a1", title="First"), _item(id="a2", title="Second")]
    payloads = serialize_activity_items(items)
    assert [p["id"] for p in payloads] == ["a1", "a2"]
    assert [p["title"] for p in payloads] == ["First", "Second"]


def test_icon_key_defaults_to_a_domain_neutral_registered_fallback() -> None:
    item = _item()
    assert item.icon_key == "history"
