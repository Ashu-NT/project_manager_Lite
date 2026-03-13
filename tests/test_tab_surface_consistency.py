from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QSizePolicy

from tests.ui_runtime_helpers import make_settings_store
from ui.modules.project_management.calendar.tab import CalendarTab
from ui.platform.admin.support.tab import SupportTab
from ui.modules.project_management.task.tab import TaskTab


class _FakeOperationalSupport:
    def __init__(self) -> None:
        self._counter = 0

    def new_incident_id(self) -> str:
        self._counter += 1
        return f"inc-test-{self._counter:03d}"

    def emit_event(self, **_kwargs):
        return _kwargs.get("trace_id", "inc-test-000")


def test_calendar_tab_uses_compact_header_and_live_badges(qapp, services):
    project = services["project_service"].create_project("Calendar Surface Project")

    tab = CalendarTab(
        work_calendar_service=services["work_calendar_service"],
        work_calendar_engine=services["work_calendar_engine"],
        scheduling_engine=services["scheduling_engine"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        user_session=services["user_session"],
    )

    assert tab.calendar_scope_badge.text() == "Mon/Tue/Wed/Thu/Fri | 8h/day"
    assert tab.calendar_holiday_badge.text() == "0 holidays"
    assert tab.calendar_project_badge.text() == project.name
    assert tab.calendar_access_badge.text() == "Manage Enabled"
    assert tab.calendar_header_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    assert tab.calendar_controls_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed


def test_support_tab_uses_compact_header_and_updates_badges(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    monkeypatch.setattr("ui.platform.admin.support.tab.get_operational_support", lambda: _FakeOperationalSupport())
    tab = SupportTab(
        settings_store=make_settings_store(repo_workspace, prefix="support-surface"),
        user_session=services["user_session"],
    )

    assert tab.support_channel_badge.text() == "Stable"
    assert tab.support_policy_badge.text() == "Manual Check"
    assert tab.support_trace_badge.text() == "Trace Ready"
    assert tab.support_header_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed

    tab.auto_check.setChecked(True)
    tab._update_support_header_badges()
    assert tab.support_policy_badge.text() == "Auto-check On"


def test_task_tab_uses_compact_control_surface_without_header_bar(qapp, services, repo_workspace):
    project = services["project_service"].create_project("Task Surface Project")
    services["task_service"].create_task(
        project.id,
        "Surface Task",
        start_date=date(2026, 4, 1),
        duration_days=2,
        priority=60,
    )

    tab = TaskTab(
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        project_resource_service=services["project_resource_service"],
        collaboration_store=services["task_collaboration_store"],
        settings_store=make_settings_store(repo_workspace, prefix="task-surface"),
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentText() == project.name
    assert not hasattr(tab, "task_header_card")
    assert tab.task_controls_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    tab._mentions_refresh_timer.stop()
