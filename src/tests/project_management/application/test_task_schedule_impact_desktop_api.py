"""Task Detail -> Schedule Impact's desktop-API surface:
get_task_schedule_overview (auto-loaded current-state facts) and
preview_task_schedule_impact (explicit "Preview Impact" what-if). Both
replace the old always-hardcoded-to-1-day get_schedule_impact.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.domain.enums import DependencyType


def _desktop_api(services, task_service):
    return ProjectManagementTasksDesktopApi(
        task_service=task_service,
        schedule_change_impact_service=ScheduleChangeImpactService(
            task_repo=task_service._task_repo,
            dependency_repo=task_service._dependency_repo,
            calendar=services["work_calendar_engine"],
            baseline_lookup=services["baseline_service"],
        ),
    )


def test_get_task_schedule_overview_reports_current_facts(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]
    project = ps.create_project("Schedule Impact Desktop API Overview", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    sched.recalculate_project_schedule(project.id)
    api = _desktop_api(services, ts)

    dto = api.get_task_schedule_overview(a.id, project.id)

    assert dto.is_available is True
    assert dto.current_start_label == "2024-01-01"
    assert dto.is_critical is True


def test_get_task_schedule_overview_is_unavailable_without_project_id(services):
    ts = services["task_service"]
    api = _desktop_api(services, ts)

    dto = api.get_task_schedule_overview("some-task", "")

    assert dto.is_available is False
    assert dto.current_start_label == "--"
    assert dto.downstream.direct_successor_count == 0


def test_get_task_schedule_overview_is_unavailable_without_impact_service(services):
    ts = services["task_service"]
    api = ProjectManagementTasksDesktopApi(task_service=ts, schedule_change_impact_service=None)

    dto = api.get_task_schedule_overview("some-task", "some-project")

    assert dto.is_available is False


def test_preview_task_schedule_impact_uses_working_day_delay_not_calendar_days(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Impact Desktop API Preview", "")
    # Friday
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 5), duration_days=1)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=1)

    assert dto.is_available is True
    # +1 working day from Friday must land on Monday -- proves the
    # desktop API is wired to analyse_working_day_delay, not the old
    # calendar-day analyse_delay.
    a_row = next(row for row in dto.affected_tasks if row.task_id == a.id)
    assert a_row.proposed_start == date(2024, 1, 8)


def test_preview_task_schedule_impact_reports_affected_downstream_tasks(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]
    project = ps.create_project("Schedule Impact Desktop API Downstream", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    sched.recalculate_project_schedule(project.id)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=3)

    assert dto.is_available is True
    assert dto.affected_count >= 1
    affected_ids = {row.task_id for row in dto.affected_tasks}
    assert b.id in affected_ids


def test_preview_task_schedule_impact_is_unavailable_for_task_without_start_date(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Impact Desktop API No Start", "")
    a = ts.create_task(project.id, "Task A", "", duration_days=2)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=1)

    assert dto.is_available is False
