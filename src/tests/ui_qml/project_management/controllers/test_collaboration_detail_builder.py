from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.collaboration.detail_builder import (
    build_detail_payload,
)


def _canonical_activity_item(**overrides) -> dict[str, object]:
    fields = {
        "id": "activity-comment:comment-9",
        "title": "Kickoff task update",
        "description": "Let's align on scope.",
        "supportingText": "",
        "actorDisplay": "grace",
        "occurredAt": "2026-03-05T14:30:00+00:00",
        "occurredAtLabel": "2026-03-05 14:30",
        "iconKey": "collaboration",
        "tone": "neutral",
        "subjectDisplay": "Project Apollo",
        "badgeLabel": "",
        "activationState": {
            "routeId": "project_management.tasks",
            "projectId": "project-1",
            "projectName": "Project Apollo",
            "taskId": "task-1",
            "commentId": "comment-9",
            "actorUsername": "grace",
            "createdAt": "2026-03-05T14:30:00+00:00",
        },
    }
    fields.update(overrides)
    return fields


def _legacy_inbox_item(**overrides) -> dict[str, object]:
    fields = {
        "id": "inbox-1",
        "title": "Reviewed budget line",
        "statusLabel": "Comment",
        "subtitle": "Project Apollo",
        "supportingText": "Looks good, approving.",
        "metaText": "2026-03-05 09:00 | @ada",
        "state": {
            "routeId": "project_management.tasks",
            "taskId": "task-1",
            "projectId": "project-1",
            "projectName": "Project Apollo",
            "actorUsername": "ada",
            "createdAt": "2026-03-05T09:00:00+00:00",
        },
    }
    fields.update(overrides)
    return fields


def test_selecting_a_canonical_activity_item_resolves_subtitle_description_and_actor() -> None:
    item = _canonical_activity_item()
    payload = build_detail_payload("activity", item, panel_item_index={})

    assert payload["subtitle"] == "Project Apollo"
    assert payload["description"] == "Let's align on scope."
    actor_field = next(f for f in payload["fields"] if f["label"] == "Actor")
    assert actor_field["value"] == "grace"
    created_field = next(f for f in payload["fields"] if f["label"] == "Created")
    assert created_field["value"] == "2026-03-05 14:30"


def test_selecting_a_legacy_inbox_item_still_resolves_fields() -> None:
    item = _legacy_inbox_item()
    payload = build_detail_payload("inbox", item, panel_item_index={})

    assert payload["subtitle"] == "Project Apollo"
    assert payload["description"] == "Looks good, approving."
    actor_field = next(f for f in payload["fields"] if f["label"] == "Actor")
    assert actor_field["value"] == "ada"


def test_canonical_activity_items_cross_reference_by_task_id_via_activation_state() -> None:
    inbox_item = _legacy_inbox_item()
    other_activity_item = _canonical_activity_item(id="activity-comment:comment-2")
    panel_item_index = {
        "activity": {other_activity_item["id"]: other_activity_item},
        "inbox": {},
        "mentions": {},
        "approvals": {},
        "audit": {},
    }

    payload = build_detail_payload("inbox", inbox_item, panel_item_index=panel_item_index)

    assert len(payload["activity"]["items"]) == 1
    assert payload["activity"]["items"][0]["id"] == "activity-comment:comment-2"


def test_related_activity_items_pass_through_the_canonical_shape_unmodified() -> None:
    inbox_item = _legacy_inbox_item()
    other_activity_item = _canonical_activity_item(id="activity-comment:comment-2")
    panel_item_index = {"activity": {other_activity_item["id"]: other_activity_item}}

    payload = build_detail_payload("inbox", inbox_item, panel_item_index=panel_item_index)

    related_activity = payload["activity"]["items"][0]
    assert related_activity["actorDisplay"] == "grace"
    assert related_activity["tone"] == "neutral"
    assert related_activity["activationState"]["taskId"] == "task-1"
