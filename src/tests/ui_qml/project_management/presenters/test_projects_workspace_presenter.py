"""Unit tests for ProjectProjectsWorkspacePresenter.

Covers: build_project_tasks_state, build_project_resources_state,
        build_project_risks_state, build_project_activity_page.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.modules.project_management.api.desktop.common.detail_pages import (
    DetailActivityDesktopDto,
    DetailActivityPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.projects import (
    ProjectResourceDesktopDto,
)
from src.core.modules.project_management.api.desktop.register import (
    RegisterEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks import TaskDesktopDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.modules.project_management.presenters.projects import (
    ProjectProjectsWorkspacePresenter,
)


# ── DTO factories ──────────────────────────────────────────────────────────────

def _task(**kw) -> TaskDesktopDto:
    return TaskDesktopDto(
        id=kw.get("id", "t-1"),
        project_id=kw.get("project_id", "p-1"),
        project_name=kw.get("project_name", "Proj"),
        name=kw.get("name", "Task One"),
        code=kw.get("code", "T-001"),
        description=kw.get("description", "Desc"),
        status=kw.get("status", "IN_PROGRESS"),
        status_label=kw.get("status_label", "In Progress"),
        start_date=kw.get("start_date", date(2025, 1, 1)),
        end_date=kw.get("end_date", date(2025, 3, 31)),
        duration_days=kw.get("duration_days", 89),
        priority=kw.get("priority", 1),
        percent_complete=kw.get("percent_complete", 50.0),
        actual_start=kw.get("actual_start", None),
        actual_end=kw.get("actual_end", None),
        deadline=kw.get("deadline", None),
        version=kw.get("version", 1),
    )


def _resource(**kw) -> ProjectResourceDesktopDto:
    return ProjectResourceDesktopDto(
        id=kw.get("id", "r-1"),
        project_id=kw.get("project_id", "p-1"),
        resource_id=kw.get("resource_id", "res-1"),
        resource_name=kw.get("resource_name", "Alice Smith"),
        role=kw.get("role", "Developer"),
        worker_type_label=kw.get("worker_type_label", "Employee"),
        hourly_rate=kw.get("hourly_rate", 80.0),
        hourly_rate_label=kw.get("hourly_rate_label", "$80/hr"),
        currency_code=kw.get("currency_code", "USD"),
        planned_hours=kw.get("planned_hours", 200.0),
        planned_hours_label=kw.get("planned_hours_label", "200h"),
        is_active=kw.get("is_active", True),
        status_label=kw.get("status_label", "Active"),
    )


def _risk(**kw) -> RegisterEntryDesktopDto:
    return RegisterEntryDesktopDto(
        id=kw.get("id", "rsk-1"),
        project_id=kw.get("project_id", "p-1"),
        project_name=kw.get("project_name", "Proj"),
        code=kw.get("code", "RSK-001"),
        entry_type=kw.get("entry_type", "RISK"),
        entry_type_label=kw.get("entry_type_label", "Risk"),
        title=kw.get("title", "Budget overrun"),
        description=kw.get("description", "Cost may exceed budget"),
        severity=kw.get("severity", "HIGH"),
        severity_label=kw.get("severity_label", "High"),
        status=kw.get("status", "OPEN"),
        status_label=kw.get("status_label", "Open"),
        owner_name=kw.get("owner_name", "Bob"),
        due_date=kw.get("due_date", date(2025, 6, 1)),
        due_date_label=kw.get("due_date_label", "01 Jun 2025"),
        impact_summary=kw.get("impact_summary", "Cost increase"),
        response_plan=kw.get("response_plan", "Monitor"),
        is_overdue=kw.get("is_overdue", False),
        version=kw.get("version", 1),
    )


def _activity_entry(**kw) -> DetailActivityDesktopDto:
    return DetailActivityDesktopDto(
        id=kw.get("id", "act-1"),
        occurred_at=kw.get("occurred_at", datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)),
        actor_id=kw.get("actor_id", "user-1"),
        action=kw.get("action", "project.update"),
        entity_type=kw.get("entity_type", "project"),
        summary=kw.get("summary", "Project updated"),
        details=kw.get("details", {}),
    )


def _presenter(
    *,
    tasks=(),
    resources=(),
    risks=(),
    activity_entries=None,
    users=(),
    employees=(),
    sites=(),
    departments=(),
):
    """Return (presenter, tasks_api_mock, projects_api_mock, register_api_mock)."""
    tasks_api = MagicMock()
    tasks_api.list_tasks.return_value = list(tasks)

    projects_api = MagicMock()
    projects_api.list_project_resources.return_value = list(resources)
    projects_api.list_project_activity_page.return_value = DetailActivityPageDesktopDto(
        items=tuple(activity_entries) if activity_entries is not None else (),
        filtered_total=len(activity_entries) if activity_entries is not None else 0,
    )

    register_api = MagicMock()
    register_api.list_entries.return_value = list(risks)

    user_api = MagicMock()
    user_api.list_users.return_value = DesktopApiResult(ok=True, data=tuple(users))

    employee_api = MagicMock()
    employee_api.list_employees.return_value = DesktopApiResult(ok=True, data=tuple(employees))

    site_api = MagicMock()
    site_api.list_sites.return_value = DesktopApiResult(ok=True, data=tuple(sites))

    department_api = MagicMock()
    department_api.list_departments.return_value = DesktopApiResult(ok=True, data=tuple(departments))

    p = ProjectProjectsWorkspacePresenter(
        desktop_api=projects_api,
        tasks_desktop_api=tasks_api,
        register_desktop_api=register_api,
        user_api=user_api,
        employee_api=employee_api,
        site_api=site_api,
        department_api=department_api,
    )
    return p, tasks_api, projects_api, register_api


# ── build_project_tasks_state ──────────────────────────────────────────────────

class TestBuildProjectTasksState:
    def test_single_task_fields_mapped_correctly(self):
        task = _task(
            id="t-42", name="Implement feature", status_label="Active",
            percent_complete=75.0, start_date=date(2025, 2, 1),
            end_date=date(2025, 4, 30), description="Core work",
        )
        p, tasks_api, _, __ = _presenter(tasks=[task])

        result = p.build_project_tasks_state(project_id="proj-1")
        items = result.project_tasks.items

        assert len(items) == 1
        item = items[0]
        assert item.id == "t-42"
        assert item.title == "Implement feature"
        assert item.status_label == "Active"
        assert item.subtitle == "75% complete"
        assert item.supporting_text == "01 Feb 2025 → 30 Apr 2025"
        assert item.meta_text == "Core work"
        tasks_api.list_tasks.assert_called_once_with("proj-1")

    def test_multiple_tasks_all_mapped(self):
        p, _, __, ___ = _presenter(tasks=[_task(id=f"t-{i}") for i in range(3)])
        result = p.build_project_tasks_state(project_id="p-1")
        assert len(result.project_tasks.items) == 3

    def test_empty_project_id_returns_empty_items_no_api_call(self):
        p, tasks_api, _, __ = _presenter()
        result = p.build_project_tasks_state(project_id="")
        assert result.project_tasks.items == ()
        tasks_api.list_tasks.assert_not_called()

    def test_whitespace_project_id_treated_as_empty(self):
        p, tasks_api, _, __ = _presenter()
        result = p.build_project_tasks_state(project_id="   ")
        assert result.project_tasks.items == ()
        tasks_api.list_tasks.assert_not_called()

    def test_zero_tasks_subtitle_uses_default_text(self):
        p, _, __, ___ = _presenter(tasks=[])
        result = p.build_project_tasks_state(project_id="p-1")
        assert result.project_tasks.subtitle == "Tasks linked to this project."

    def test_non_empty_tasks_subtitle_shows_count(self):
        p, _, __, ___ = _presenter(tasks=[_task()])
        result = p.build_project_tasks_state(project_id="p-1")
        assert "1 task" in result.project_tasks.subtitle

    def test_none_dates_formatted_as_not_scheduled(self):
        task = _task(start_date=None, end_date=None)
        p, _, __, ___ = _presenter(tasks=[task])
        result = p.build_project_tasks_state(project_id="p-1")
        assert result.project_tasks.items[0].supporting_text == "Not scheduled → Not scheduled"

    def test_selected_project_id_stored_on_view_model(self):
        p, _, __, ___ = _presenter()
        result = p.build_project_tasks_state(project_id="proj-99")
        assert result.selected_project_id == "proj-99"

    def test_percent_complete_zero_displays_correctly(self):
        task = _task(percent_complete=0.0)
        p, _, __, ___ = _presenter(tasks=[task])
        result = p.build_project_tasks_state(project_id="p-1")
        assert result.project_tasks.items[0].subtitle == "0% complete"


# ── build_project_resources_state ──────────────────────────────────────────────

class TestBuildProjectResourcesState:
    def test_single_resource_fields_mapped_correctly(self):
        res = _resource(
            id="r-99", resource_name="Bob Jones", role="PM",
            planned_hours_label="320h", hourly_rate_label="$90/hr", status_label="Active",
        )
        p, _, projects_api, __ = _presenter(resources=[res])

        result = p.build_project_resources_state(project_id="proj-1")
        items = result.project_resources.items

        assert len(items) == 1
        item = items[0]
        assert item.id == "r-99"
        assert item.title == "Bob Jones"
        assert item.subtitle == "PM"
        assert item.supporting_text == "320h"
        assert item.meta_text == "$90/hr"
        assert item.status_label == "Active"
        projects_api.list_project_resources.assert_called_once_with("proj-1")

    def test_empty_role_falls_back_to_team_member(self):
        p, _, __, ___ = _presenter(resources=[_resource(role="")])
        result = p.build_project_resources_state(project_id="p-1")
        assert result.project_resources.items[0].subtitle == "Team member"

    def test_empty_project_id_skips_api(self):
        p, _, projects_api, __ = _presenter()
        result = p.build_project_resources_state(project_id="")
        assert result.project_resources.items == ()
        projects_api.list_project_resources.assert_not_called()

    def test_multiple_resources_all_mapped(self):
        p, _, __, ___ = _presenter(resources=[_resource(id=f"r-{i}") for i in range(4)])
        result = p.build_project_resources_state(project_id="p-1")
        assert len(result.project_resources.items) == 4

    def test_selected_project_id_stored(self):
        p, _, __, ___ = _presenter()
        result = p.build_project_resources_state(project_id="p-77")
        assert result.selected_project_id == "p-77"


# ── build_project_risks_state ──────────────────────────────────────────────────

class TestBuildProjectRisksState:
    def test_single_risk_fields_mapped_correctly(self):
        risk = _risk(
            id="rsk-7", title="Schedule slip", severity_label="Critical",
            status_label="Mitigating", impact_summary="Delay delivery",
            due_date_label="15 Jul 2025",
        )
        p, _, __, register_api = _presenter(risks=[risk])

        result = p.build_project_risks_state(project_id="proj-1")
        items = result.project_risks.items

        assert len(items) == 1
        item = items[0]
        assert item.id == "rsk-7"
        assert item.title == "Schedule slip"
        assert item.status_label == "Critical"
        assert item.subtitle == "Mitigating"
        assert item.supporting_text == "Delay delivery"
        assert item.meta_text == "15 Jul 2025"

    def test_api_called_with_risk_entry_type(self):
        p, _, __, register_api = _presenter()
        p.build_project_risks_state(project_id="p-1")
        register_api.list_entries.assert_called_once_with(
            project_id="p-1",
            entry_type="RISK",
        )

    def test_empty_project_id_skips_api(self):
        p, _, __, register_api = _presenter()
        result = p.build_project_risks_state(project_id="")
        assert result.project_risks.items == ()
        register_api.list_entries.assert_not_called()

    def test_empty_impact_summary_uses_fallback_text(self):
        p, _, __, ___ = _presenter(risks=[_risk(impact_summary="")])
        result = p.build_project_risks_state(project_id="p-1")
        assert result.project_risks.items[0].supporting_text == "No impact summary recorded."

    def test_multiple_risks_all_mapped(self):
        p, _, __, ___ = _presenter(risks=[_risk(id=f"rsk-{i}") for i in range(5)])
        result = p.build_project_risks_state(project_id="p-1")
        assert len(result.project_risks.items) == 5

    def test_non_empty_risks_subtitle_shows_count(self):
        p, _, __, ___ = _presenter(risks=[_risk()])
        result = p.build_project_risks_state(project_id="p-1")
        assert "1 risk" in result.project_risks.subtitle

    def test_zero_risks_subtitle_uses_default_text(self):
        p, _, __, ___ = _presenter(risks=[])
        result = p.build_project_risks_state(project_id="p-1")
        assert result.project_risks.subtitle == "Risks and mitigation records."


# ── build_project_activity_page ─────────────────────────────────────────────

class TestBuildProjectActivityPage:
    def test_single_entry_maps_to_the_canonical_activity_shape(self):
        entry = _activity_entry(
            id="act-42", action="project.update", summary="Renamed project",
            occurred_at=datetime(2026, 3, 5, 14, 45, tzinfo=timezone.utc),
        )
        p, _, projects_api, __ = _presenter(activity_entries=[entry])

        result = p.build_project_activity_page(project_id="proj-1")
        items = result["items"]

        assert len(items) == 1
        item = items[0]
        assert item["id"] == "act-42"
        assert item["title"] == "Renamed project"
        # No user_api/employee_api match for "user-1" -> falls back to "System".
        assert item["actorDisplay"] == "System"
        assert item["tone"] == "warning"
        assert item["statusLabel"] == ""
        assert item["occurredAtLabel"] == "05 Mar 2026 14:45"
        projects_api.list_project_activity_page.assert_called_once_with(
            "proj-1", search_text="", category="all", page=1, page_size=25,
        )

    def test_actor_resolved_from_employee_full_name(self):
        """The user's own guidance: most users are employees, so the linked
        Employee's full_name should win over the bare User account fields."""
        entry = _activity_entry(actor_id="user-1")
        p, _, __, ___ = _presenter(
            activity_entries=[entry],
            users=[SimpleNamespace(id="user-1", display_name="jdoe", username="jdoe")],
            employees=[SimpleNamespace(id="emp-1", user_id="user-1", full_name="Jane Doe")],
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["actorDisplay"] == "Jane Doe"

    def test_actor_falls_back_to_user_display_name_when_no_employee_match(self):
        entry = _activity_entry(actor_id="user-1")
        p, _, __, ___ = _presenter(
            activity_entries=[entry],
            users=[SimpleNamespace(id="user-1", display_name="Jamie Admin", username="jadmin")],
            employees=[SimpleNamespace(id="emp-1", user_id="user-2", full_name="Someone Else")],
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["actorDisplay"] == "Jamie Admin"

    def test_actor_falls_back_to_username_when_no_display_name(self):
        entry = _activity_entry(actor_id="user-1")
        p, _, __, ___ = _presenter(
            activity_entries=[entry],
            users=[SimpleNamespace(id="user-1", display_name=None, username="jadmin")],
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["actorDisplay"] == "jadmin"

    def test_missing_actor_id_is_a_system_actor_not_unknown_user(self):
        entry = _activity_entry(actor_id=None)
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["actorDisplay"] == "System"

    def test_field_changes_summary_shows_from_and_to(self):
        entry = _activity_entry(
            action="project.update",
            details={
                "changes": {
                    "status": {"from": "PLANNED", "to": "ACTIVE"},
                    "name": {"from": "Old Name", "to": "New Name"},
                }
            },
        )
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        summary = result["items"][0]["supportingText"]
        assert "Name: Old Name → New Name" in summary
        assert "Status: Planned → Active" in summary

    def test_field_changes_summary_resolves_site_id_to_site_name(self):
        entry = _activity_entry(
            details={"changes": {"site_id": {"from": "site-a", "to": "site-b"}}},
        )
        p, _, __, ___ = _presenter(
            activity_entries=[entry],
            sites=[
                SimpleNamespace(id="site-a", name="Hamburg Yard"),
                SimpleNamespace(id="site-b", name="Rotterdam Yard"),
            ],
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["supportingText"] == "Site: Hamburg Yard → Rotterdam Yard"

    def test_field_changes_summary_falls_back_to_raw_id_when_unresolved(self):
        entry = _activity_entry(
            details={"changes": {"department_id": {"from": None, "to": "dept-9"}}},
        )
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["supportingText"] == "Department: - → dept-9"

    def test_no_changes_yields_empty_supporting_text(self):
        entry = _activity_entry(action="project.create", details={})
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["supportingText"] == ""

    def test_multiple_entries_all_mapped(self):
        p, _, __, ___ = _presenter(
            activity_entries=[_activity_entry(id=f"act-{i}") for i in range(3)]
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert len(result["items"]) == 3

    def test_falls_back_to_humanized_action_when_summary_equals_action(self):
        entry = _activity_entry(action="project.set_status", summary="project.set_status")
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["title"] == "Project Set Status"

    def test_creation_action_gets_success_tone_and_no_badge(self):
        p, _, __, ___ = _presenter(activity_entries=[_activity_entry(action="project.create")])
        result = p.build_project_activity_page(project_id="p-1")
        item = result["items"][0]
        assert item["tone"] == "success"
        assert item["statusLabel"] == ""

    def test_deletion_action_gets_danger_tone_and_no_badge(self):
        p, _, __, ___ = _presenter(activity_entries=[_activity_entry(action="project.delete")])
        result = p.build_project_activity_page(project_id="p-1")
        item = result["items"][0]
        assert item["tone"] == "danger"
        assert item["statusLabel"] == ""

    def test_subject_display_reflects_entity_type(self):
        entry = _activity_entry(entity_type="project_resource")
        p, _, __, ___ = _presenter(activity_entries=[entry])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["subjectDisplay"] == "Project Resource"

    def test_no_activation_state_for_project_own_activity_rows(self):
        """Project Activity items describe the project already being viewed --
        there is no separate destination to navigate to, so they must not be
        presented as clickable."""
        p, _, __, ___ = _presenter(activity_entries=[_activity_entry()])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"][0]["activationState"] is None

    def test_empty_activity_yields_empty_items(self):
        p, _, __, ___ = _presenter(activity_entries=[])
        result = p.build_project_activity_page(project_id="p-1")
        assert result["items"] == []

    def test_search_category_and_paging_are_forwarded_to_the_desktop_api(self):
        p, _, projects_api, __ = _presenter(activity_entries=[])
        p.build_project_activity_page(
            project_id="p-1", search_text="renamed", category="project", page=2, page_size=10,
        )
        projects_api.list_project_activity_page.assert_called_once_with(
            "p-1", search_text="renamed", category="project", page=2, page_size=10,
        )

    def test_paging_metadata_is_carried_through_from_the_desktop_page(self):
        p, _, projects_api, __ = _presenter(activity_entries=[_activity_entry()])
        projects_api.list_project_activity_page.return_value = DetailActivityPageDesktopDto(
            items=(_activity_entry(),), filtered_total=42, page=3, page_size=10,
            sort_key="occurredAt", sort_direction="desc",
        )
        result = p.build_project_activity_page(project_id="p-1")
        assert result["total"] == 42
        assert result["page"] == 3
        assert result["pageSize"] == 10
        assert result["sortKey"] == "occurredAt"
        assert result["sortDirection"] == "desc"
