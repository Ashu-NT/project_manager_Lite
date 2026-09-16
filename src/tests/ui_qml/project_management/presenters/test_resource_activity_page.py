from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.ui_qml.modules.project_management.presenters.resources.context_builder import (
    build_resource_activity_page,
)


def _activity_item(**overrides) -> SimpleNamespace:
    fields = dict(
        id="act-1",
        resource_id="res-1",
        occurred_at=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        event_type="resource.skill.add",
        category="capability",
        actor_id="user-1",
        summary="Added Planning skill",
        source_type="resource",
        source_id="res-1",
        project_id=None,
        task_id=None,
        can_open_source=False,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _page(items):
    return SimpleNamespace(items=tuple(items), filtered_total=len(items), page=1, page_size=25,
                            sort_key="occurredAt", sort_direction="desc")


def _desktop_api(items):
    api = MagicMock()
    api.list_resource_activity_page.return_value = _page(items)
    return api


class TestBuildResourceActivityPage:
    def test_maps_title_timestamp_and_category_badge(self):
        item = _activity_item()
        result = build_resource_activity_page(_desktop_api([item]), "res-1")

        mapped = result["items"][0]
        assert mapped["id"] == "act-1"
        assert mapped["title"] == "Added Planning skill"
        assert mapped["occurredAtLabel"] == "05 Mar 2026 14:30"
        assert mapped["statusLabel"] == "Capability"

    def test_actor_resolved_from_employee_full_name(self):
        item = _activity_item(actor_id="user-1")
        user_api = MagicMock()
        from src.core.platform.api.desktop.models.common import DesktopApiResult
        user_api.list_users.return_value = DesktopApiResult(
            ok=True, data=(SimpleNamespace(id="user-1", display_name="jdoe", username="jdoe"),)
        )
        employee_api = MagicMock()
        employee_api.list_employees.return_value = DesktopApiResult(
            ok=True, data=(SimpleNamespace(id="emp-1", user_id="user-1", full_name="Jane Doe"),)
        )

        result = build_resource_activity_page(
            _desktop_api([item]), "res-1", user_api=user_api, employee_api=employee_api,
        )

        assert result["items"][0]["actorDisplay"] == "Jane Doe"

    def test_missing_actor_id_is_a_system_actor(self):
        item = _activity_item(actor_id=None)
        result = build_resource_activity_page(_desktop_api([item]), "res-1")
        assert result["items"][0]["actorDisplay"] == "System"

    def test_tone_derives_from_the_structured_event_type_not_the_category_text(self):
        item = _activity_item(event_type="assignment.delete", category="assignments")
        result = build_resource_activity_page(_desktop_api([item]), "res-1")
        assert result["items"][0]["tone"] == "danger"

    def test_activation_state_carries_navigation_targets_when_openable(self):
        item = _activity_item(
            source_type="task", task_id="task-1", project_id="project-1", can_open_source=True,
        )
        result = build_resource_activity_page(_desktop_api([item]), "res-1")
        assert result["items"][0]["activationState"] == {
            "sourceType": "task", "sourceId": "res-1", "projectId": "project-1", "taskId": "task-1",
        }

    def test_no_activation_state_when_source_cannot_be_opened(self):
        item = _activity_item(can_open_source=False)
        result = build_resource_activity_page(_desktop_api([item]), "res-1")
        assert result["items"][0]["activationState"] is None

    def test_subject_display_reflects_source_type(self):
        item = _activity_item(source_type="project")
        result = build_resource_activity_page(_desktop_api([item]), "res-1")
        assert result["items"][0]["subjectDisplay"] == "Project"

    def test_paging_metadata_is_carried_through(self):
        result = build_resource_activity_page(_desktop_api([_activity_item()]), "res-1")
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["pageSize"] == 25
