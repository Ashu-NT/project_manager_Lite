"""Task Detail -> Schedule Impact's desktop-API surface:
get_task_schedule_overview (auto-loaded current-state facts) and
preview_task_schedule_impact (explicit "Preview Impact" what-if). Both
replace the old always-hardcoded-to-1-day get_schedule_impact.
"""
from __future__ import annotations

from datetime import date

from src.application.runtime.desktop_api_registry import build_desktop_api_registry
from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.application.scheduling.forecasting.queries.change_impact import (
    ScheduleChangeImpactQueryHandler,
)
from src.core.modules.project_management.domain.enums import DependencyType


def test_schedule_impact_uses_the_composition_built_query(services):
    api = build_desktop_api_registry(services).project_management_tasks
    assert api._schedule_change_impact_query is services["schedule_change_impact_query"]
    assert api._schedule_change_impact_query._task_repo is services["task_lookup_query"]._task_repo


def _desktop_api(services, task_service):
    return ProjectManagementTasksDesktopApi(
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_detail_query=task_service, task_assignment_commands=task_service,
        schedule_change_impact_query=ScheduleChangeImpactQueryHandler(
            task_repo=services["task_lookup_query"]._task_repo,
            dependency_repo=services["task_dependency_diagnostics"]._dependency_repo,
            calendar=services["work_calendar_engine"],
            baseline_lookup=services['baseline_query'],
        ),
    )


def test_get_task_schedule_overview_reports_current_facts(services):
    services['project_query']
    ts = services['task_lookup_query']
    sched = services["scheduling_engine"]
    project = services['project_create'].create_project("Schedule Impact Desktop API Overview", "")
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    sched.recalculate_project_schedule(project.id)
    api = _desktop_api(services, ts)

    dto = api.get_task_schedule_overview(a.id, project.id)

    assert dto.is_available is True
    assert dto.current_start_label == "2024-01-01"
    assert dto.is_critical is True


def test_get_task_schedule_overview_is_unavailable_without_project_id(services):
    ts = services['task_lookup_query']
    api = _desktop_api(services, ts)

    dto = api.get_task_schedule_overview("some-task", "")

    assert dto.is_available is False
    assert dto.current_start_label == "--"
    assert dto.downstream.direct_successor_count == 0


def test_get_task_schedule_overview_is_unavailable_without_impact_service(services):
    services['task_lookup_query']
    api = ProjectManagementTasksDesktopApi(task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], schedule_change_impact_query=None)

    dto = api.get_task_schedule_overview("some-task", "some-project")

    assert dto.is_available is False


def test_preview_task_schedule_impact_uses_working_day_delay_not_calendar_days(services):
    services['project_query']
    ts = services['task_lookup_query']
    project = services['project_create'].create_project("Schedule Impact Desktop API Preview", "")
    # Friday
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2024, 1, 5), duration_days=1)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=1)

    assert dto.is_available is True
    # +1 working day from Friday must land on Monday -- proves the
    # desktop API is wired to analyse_working_day_delay, not the old
    # calendar-day analyse_delay.
    a_row = next(row for row in dto.affected_tasks if row.task_id == a.id)
    assert a_row.proposed_start == date(2024, 1, 8)


def test_preview_task_schedule_impact_reports_affected_downstream_tasks(services):
    services['project_query']
    ts = services['task_lookup_query']
    sched = services["scheduling_engine"]
    project = services['project_create'].create_project("Schedule Impact Desktop API Downstream", "")
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = services['task_lifecycle_commands'].create_task(project.id, "Task B", "", duration_days=2)
    services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    sched.recalculate_project_schedule(project.id)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=3)

    assert dto.is_available is True
    assert dto.affected_count >= 1
    affected_ids = {row.task_id for row in dto.affected_tasks}
    assert b.id in affected_ids


def test_preview_task_schedule_impact_is_unavailable_for_task_without_start_date(services):
    services['project_query']
    ts = services['task_lookup_query']
    project = services['project_create'].create_project("Schedule Impact Desktop API No Start", "")
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", duration_days=2)
    api = _desktop_api(services, ts)

    dto = api.preview_task_schedule_impact(a.id, project.id, delay_working_days=1)

    assert dto.is_available is False
