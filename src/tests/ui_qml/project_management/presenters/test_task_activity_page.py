from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.core.modules.project_management.api.desktop.common.detail_pages import (
    DetailActivityDesktopDto,
    DetailActivityPageDesktopDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.modules.project_management.presenters.tasks import (
    ProjectTasksWorkspacePresenter,
)


def _activity_entry(**kw) -> DetailActivityDesktopDto:
    fields = dict(
        id="act-1",
        occurred_at=datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc),
        actor_id="user-1",
        action="task.update_progress",
        entity_type="task",
        summary="Progress updated",
        details={},
    )
    fields.update(kw)
    return DetailActivityDesktopDto(**fields)


def _presenter(*, activity_entries=None, users=(), employees=()):
    """Return (presenter, tasks_api_mock)."""
    tasks_api = MagicMock()
    tasks_api.list_task_activity_page.return_value = DetailActivityPageDesktopDto(
        items=tuple(activity_entries) if activity_entries is not None else (),
        filtered_total=len(activity_entries) if activity_entries is not None else 0,
    )

    user_api = MagicMock()
    user_api.list_users.return_value = DesktopApiResult(ok=True, data=tuple(users))

    employee_api = MagicMock()
    employee_api.list_employees.return_value = DesktopApiResult(ok=True, data=tuple(employees))

    p = ProjectTasksWorkspacePresenter(
        desktop_api=tasks_api,
        collaboration_desktop_api=MagicMock(),
        timesheets_desktop_api=MagicMock(),
        user_api=user_api,
        employee_api=employee_api,
    )
    return p, tasks_api


class TestBuildTaskActivityPage:
    def test_single_entry_maps_to_the_canonical_activity_shape(self):
        entry = _activity_entry(
            id="act-9", action="task.set_status", summary="Marked in progress",
            occurred_at=datetime(2026, 3, 5, 14, 45, tzinfo=timezone.utc),
        )
        p, tasks_api = _presenter(activity_entries=[entry])

        result = p.build_task_activity_page(task_id="task-1")
        items = result["items"]

        assert len(items) == 1
        item = items[0]
        assert item["id"] == "act-9"
        assert item["title"] == "Marked in progress"
        assert item["actorDisplay"] == "System"
        assert item["tone"] == "neutral"  # "set_status" matches no danger/warning/success verb keyword
        assert item["statusLabel"] == ""
        assert item["occurredAtLabel"] == "05 Mar 2026 14:45"
        tasks_api.list_task_activity_page.assert_called_once_with(
            "task-1", search_text="", category="all", page=1, page_size=25,
        )

    def test_actor_resolved_from_employee_full_name(self):
        entry = _activity_entry(actor_id="user-1")
        p, _ = _presenter(
            activity_entries=[entry],
            users=[SimpleNamespace(id="user-1", display_name="jdoe", username="jdoe")],
            employees=[SimpleNamespace(id="emp-1", user_id="user-1", full_name="Jane Doe")],
        )
        result = p.build_task_activity_page(task_id="task-1")
        assert result["items"][0]["actorDisplay"] == "Jane Doe"

    def test_missing_actor_id_is_a_system_actor(self):
        entry = _activity_entry(actor_id=None)
        p, _ = _presenter(activity_entries=[entry])
        result = p.build_task_activity_page(task_id="task-1")
        assert result["items"][0]["actorDisplay"] == "System"

    def test_creation_action_gets_success_tone_and_no_badge(self):
        p, _ = _presenter(activity_entries=[_activity_entry(action="task.create")])
        item = p.build_task_activity_page(task_id="task-1")["items"][0]
        assert item["tone"] == "success"
        assert item["statusLabel"] == ""

    def test_deletion_action_gets_danger_tone_and_no_badge(self):
        p, _ = _presenter(activity_entries=[_activity_entry(action="task.delete")])
        item = p.build_task_activity_page(task_id="task-1")["items"][0]
        assert item["tone"] == "danger"
        assert item["statusLabel"] == ""

    def test_subject_display_reflects_entity_type(self):
        entry = _activity_entry(entity_type="task_assignment")
        p, _ = _presenter(activity_entries=[entry])
        result = p.build_task_activity_page(task_id="task-1")
        assert result["items"][0]["subjectDisplay"] == "Task Assignment"

    def test_no_activation_state_for_task_own_activity_rows(self):
        p, _ = _presenter(activity_entries=[_activity_entry()])
        result = p.build_task_activity_page(task_id="task-1")
        assert result["items"][0]["activationState"] is None

    def test_multiple_entries_all_mapped(self):
        p, _ = _presenter(activity_entries=[_activity_entry(id=f"act-{i}") for i in range(3)])
        result = p.build_task_activity_page(task_id="task-1")
        assert len(result["items"]) == 3

    def test_empty_activity_yields_empty_items(self):
        p, _ = _presenter(activity_entries=[])
        result = p.build_task_activity_page(task_id="task-1")
        assert result["items"] == []

    def test_search_category_and_paging_are_forwarded_to_the_desktop_api(self):
        p, tasks_api = _presenter(activity_entries=[])
        p.build_task_activity_page(
            task_id="task-1", search_text="progress", category="task", page=2, page_size=10,
        )
        tasks_api.list_task_activity_page.assert_called_once_with(
            "task-1", search_text="progress", category="task", page=2, page_size=10,
        )

    def test_paging_metadata_is_carried_through_from_the_desktop_page(self):
        p, tasks_api = _presenter(activity_entries=[_activity_entry()])
        tasks_api.list_task_activity_page.return_value = DetailActivityPageDesktopDto(
            items=(_activity_entry(),), filtered_total=17, page=2, page_size=10,
            sort_key="occurredAt", sort_direction="desc",
        )
        result = p.build_task_activity_page(task_id="task-1")
        assert result["total"] == 17
        assert result["page"] == 2
        assert result["pageSize"] == 10
        assert result["sortKey"] == "occurredAt"
        assert result["sortDirection"] == "desc"
