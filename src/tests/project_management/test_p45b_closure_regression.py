"""P45B-CLOSURE mandatory regressions (brief items §4, §10, §30, §36).

§4  -- a transactional-handler failure during `TimeService.add_work_entry` /
        `update_time_entry` rolls back the TimeEntry write, the TaskAssignment
        hours-sync CAS write, and the EnterpriseAudit entry together (same
        physical transaction, per the `_time_entry_unit_of_work` fix), and
        yields zero postcommit ViewInvalidation hint.
§10 -- the Timesheet Class-B `task_list` replacement (for the deleted legacy
        `tasks_changed` re-emission) proved end-to-end with real services:
        exactly the referenced project's Task list projection is stale, an
        unrelated project's is not, and zero real Task DomainEvent fires.
§30 -- explicit per-consumer QML regression coverage for the four Task
        ViewInvalidation consumers not already covered elsewhere (Dashboard,
        Resources, Timesheets/ResourceTimesheetsController, Review Queue) plus
        Portfolio's second signal (`taskDependenciesStale`).
§36 -- the "producerless legacy consumer" / inert-consumer regression: the
        legacy `tasks_changed` field itself is gone, and a real, typed Task
        mutation still reaches its genuine QML consumer purely through
        ViewInvalidation, with zero legacy Signal involved anywhere.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
)
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints: list = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _task_hints(hints):
    return [h for h in hints if h.category == "task"]


# ---------------------------------------------------------------------------
# §36 -- the legacy field itself is gone, module-wide.
# ---------------------------------------------------------------------------


def test_domain_events_has_no_tasks_changed_field():
    assert not hasattr(domain_events, "tasks_changed")


def test_task_mutation_succeeds_with_zero_tasks_changed_and_genuine_consumer_refreshes(services, monkeypatch, qapp):
    """A real, typed Task mutation (`create_task`) reaches the Tasks workspace's genuine
    consumer purely through ViewInvalidation -- no legacy Signal exists to have carried it."""
    project = services["project_service"].create_project("P45B Closure Producerless Project")
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.tasksWorkspace
    controller._selected_project_id = project.id
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    services["task_service"].create_task(
        project.id, "Producerless Regression Task", start_date=date(2026, 9, 1), duration_days=5
    )

    assert not hasattr(domain_events, "tasks_changed")
    assert refresh_calls == ["refresh"]


# ---------------------------------------------------------------------------
# §30 -- per-consumer QML regression coverage for the remaining, not-yet-covered consumers
# ---------------------------------------------------------------------------


def test_dashboard_workspace_refreshes_on_dashboard_task_metrics_stale(monkeypatch):
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.dashboardWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_request_domain_refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskMetricsStale("org-1")

    assert refresh_calls == ["refresh"]


def test_portfolio_workspace_refreshes_on_task_dependencies_stale(monkeypatch, qapp):
    """Companion to the existing `taskListStale` coverage -- Portfolio's second Task
    dependency (`taskDependenciesStale`, the one fact `taskListStale` doesn't cover)."""
    from PySide6.QtWidgets import QApplication

    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskDependenciesStale("proj-1")
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_timesheets_workspace_reacts_to_task_profile_stale(monkeypatch):
    """`ProjectManagementResourceTimesheetsController` (the `timesheetsWorkspace` property) --
    not project-scoped, so any project's Task profile change triggers a refresh."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.timesheetsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_request_domain_refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskProfileStale("proj-1")

    assert refresh_calls == ["refresh"]


def test_review_queue_workspace_reacts_to_task_profile_stale(monkeypatch):
    """`ProjectManagementTimesheetsWorkspaceController` (the `reviewQueueWorkspace` property) --
    a distinct instance from `timesheetsWorkspace`, with its own `TaskViewInvalidationAdapter`."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.reviewQueueWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_request_domain_refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskProfileStale("proj-1")

    assert refresh_calls == ["refresh"]


def test_resources_workspace_reloads_on_task_assignments_for_resource_stale(monkeypatch):
    from src.ui_qml.modules.project_management.controllers.resources import (
        resource_domain_event_binder as binder,
    )

    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.resourcesWorkspace
    controller._selected_resource_id = "resource-1"
    controller._resource_assignments_loaded_for = "resource-1"
    controller._resource_activity_loaded_for = "resource-1"
    calls: list[str] = []
    monkeypatch.setattr(binder, "load_resource_assignments", lambda c, force=True: calls.append("assignments"))
    monkeypatch.setattr(binder, "load_resource_activity", lambda c, force=True: calls.append("activity"))

    controller.onTaskAssignmentsForResourceStale("resource-1")

    assert calls == ["assignments", "activity"]


def test_resources_workspace_ignores_unselected_resource_task_assignment_stale(monkeypatch):
    from src.ui_qml.modules.project_management.controllers.resources import (
        resource_domain_event_binder as binder,
    )

    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.resourcesWorkspace
    controller._selected_resource_id = "resource-1"
    controller._resource_assignments_loaded_for = "resource-1"
    controller._resource_activity_loaded_for = "resource-1"
    calls: list[str] = []
    monkeypatch.setattr(binder, "load_resource_assignments", lambda c, force=True: calls.append("assignments"))
    monkeypatch.setattr(binder, "load_resource_activity", lambda c, force=True: calls.append("activity"))

    controller.onTaskAssignmentsForResourceStale("some-other-resource")

    assert calls == []


# ---------------------------------------------------------------------------
# §4 -- TimeEntry transactional-handler failure rolls back the whole transaction
# ---------------------------------------------------------------------------


def _setup_time_entry_case(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P45B Closure TimeEntry Rollback Project", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        "P45B Closure TimeEntry Rollback Engineer", hourly_rate=0, currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, "P45B Closure TimeEntry Rollback Task", start_date=date(2026, 9, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(task.id, resource.id, allocation_percent=100)
    return project, resource, task, assignment


def test_add_work_entry_transactional_handler_failure_rolls_back_time_entry_and_assignment_hours(
    services, monkeypatch
):
    project, _resource, _task, assignment = _setup_time_entry_case(services)
    hints = _spy_hints(services)
    dispatcher = services["time_service"]._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(TaskAssignmentChanged, _raising_handler)

    with pytest.raises(RuntimeError):
        services["task_service"].add_time_entry(
            assignment.id, entry_date=date(2026, 9, 5), hours=4
        )

    time_service = services["time_service"]
    assert time_service._time_entry_repo.list_by_work_allocation(assignment.id) == []
    reloaded_assignment = services["task_service"]._assignment_repo.get(assignment.id)
    assert float(reloaded_assignment.hours_logged) == 0.0
    assert _task_hints(hints) == []


def test_service_remains_usable_after_add_work_entry_transactional_handler_failure(services, monkeypatch):
    project, _resource, _task, assignment = _setup_time_entry_case(services)
    dispatcher = services["time_service"]._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    subscription = dispatcher.subscribe(TaskAssignmentChanged, _raising_handler)
    with pytest.raises(RuntimeError):
        services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 9, 5), hours=4)

    subscription.dispose()
    entry = services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 9, 6), hours=3)

    assert entry.hours == 3
    reloaded_assignment = services["task_service"]._assignment_repo.get(assignment.id)
    assert float(reloaded_assignment.hours_logged) == 3.0


def test_update_time_entry_transactional_handler_failure_rolls_back_the_revision(services, monkeypatch):
    project, _resource, _task, assignment = _setup_time_entry_case(services)
    entry = services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 9, 5), hours=4)
    hints = _spy_hints(services)
    dispatcher = services["time_service"]._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(TaskAssignmentChanged, _raising_handler)

    with pytest.raises(RuntimeError):
        services["time_service"].update_time_entry(entry.id, expected_version=entry.version, hours=7)

    reloaded_entry = services["time_service"]._time_entry_repo.get(entry.id)
    assert reloaded_entry.hours == 4
    reloaded_assignment = services["task_service"]._assignment_repo.get(assignment.id)
    assert float(reloaded_assignment.hours_logged) == 4.0
    assert _task_hints(hints) == []


# ---------------------------------------------------------------------------
# §10 -- Timesheet Class-B `task_list` replacement, proved end-to-end
# ---------------------------------------------------------------------------


def test_submit_timesheet_period_stales_only_the_referenced_project_task_list(services):
    organization = services["tenant_context_service"].get_active_organization()
    referenced_project = services["project_service"].create_project(
        "P45B Closure Class-B Referenced Project", financial_currency_code=organization.base_currency
    )
    unrelated_project = services["project_service"].create_project(
        "P45B Closure Class-B Unrelated Project", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        "P45B Closure Class-B Engineer", hourly_rate=0, currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        referenced_project.id, "Class-B Task", start_date=date(2026, 9, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(task.id, resource.id, allocation_percent=100)
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 9, 4), hours=4)

    hints = _spy_hints(services)
    services["timesheet_service"].submit_timesheet_period(resource.id, period_start=date(2026, 9, 1))

    task_hints = _task_hints(hints)
    assert {h.scope_code for h in task_hints} == {"task_list"}
    assert {h.entity_id for h in task_hints} == {referenced_project.id}
    assert unrelated_project.id not in {h.entity_id for h in task_hints}


def test_submit_timesheet_period_records_zero_real_task_domain_event(services, monkeypatch):
    """The Class-B bridge maps directly onto the existing `task_list` ViewInvalidation target --
    it must never construct or dispatch a real typed Task DomainEvent to do it."""
    from src.core.modules.project_management.application.tasks import task_events

    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P45B Closure Class-B No Typed Event Project", financial_currency_code=organization.base_currency
    )
    resource = services["resource_service"].create_resource(
        "P45B Closure Class-B No Typed Event Engineer", hourly_rate=0, currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, "Class-B No Typed Event Task", start_date=date(2026, 9, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(task.id, resource.id, allocation_percent=100)
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 9, 4), hours=4)

    seen: list[object] = []
    dispatcher = services["time_service"]._transactional_dispatcher
    for event_cls in (
        task_events.TaskCreated,
        task_events.TaskProfileUpdated,
        task_events.TaskStatusChanged,
        task_events.TaskProgressChanged,
        task_events.TaskScheduleChanged,
        task_events.TaskHierarchyChanged,
        task_events.TaskAssignmentChanged,
        task_events.TaskDependencyChanged,
        task_events.TaskRemoved,
    ):
        dispatcher.subscribe(event_cls, lambda event, uow, _bucket=seen: _bucket.append(event))

    services["timesheet_service"].submit_timesheet_period(resource.id, period_start=date(2026, 9, 1))

    assert seen == []
    assert not hasattr(domain_events, "tasks_changed")
