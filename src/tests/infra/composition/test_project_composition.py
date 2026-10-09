from __future__ import annotations

from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
    ProjectProfileUpdated,
    ProjectRemoved,
    ProjectStatusChanged,
)
from src.core.modules.project_management.application.resources.project_resources.project_resource_events import (
    ProjectResourceAssignmentChanged,
)
from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChanged,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
    TaskCreated,
    TaskDependencyChanged,
    TaskHierarchyChanged,
    TaskProfileUpdated,
    TaskProgressChanged,
    TaskRemoved,
    TaskScheduleChanged,
    TaskStatusChanged,
)
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChanged,
)


def test_project_events_share_one_post_commit_handler(services) -> None:
    project = services["project_service"]
    tasks = services["task_service"]
    bus = project._uow_factory._post_commit_bus

    assert bus is tasks._task_uow_factory._post_commit_bus
    event_types = (
        ProjectCreated,
        ProjectProfileUpdated,
        ProjectStatusChanged,
        ProjectRemoved,
        ProjectResourceAssignmentChanged,
    )
    handlers = [
        next(
            handler
            for handler in bus._handlers[event_type]
            if handler.__name__ == "handle_project_event"
        )
        for event_type in event_types
    ]
    assert all(
        sum(handler.__name__ == "handle_project_event" for handler in bus._handlers[event_type]) == 1
        for event_type in event_types
    )
    assert all(handler is handlers[0] for handler in handlers)


def test_project_uow_factory_opens_a_fresh_session(services, session) -> None:
    project = services["project_service"]
    scoped_session = project._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_register_uses_shared_bus_and_one_invalidation_handler(services, session) -> None:
    project_bus = services["project_service"]._uow_factory._post_commit_bus
    register_uow = services["register_service"]._uow_factory
    assert register_uow._post_commit_bus is project_bus
    assert sum(
        handler.__name__ == "handle_register_entry_event"
        for handler in project_bus._handlers[RegisterEntryChanged]
    ) == 1
    scoped_session = register_uow._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_task_events_share_one_post_commit_handler_and_fresh_uow(services, session) -> None:
    task_uow = services["task_service"]._task_uow_factory
    bus = services["project_service"]._uow_factory._post_commit_bus
    assert task_uow._post_commit_bus is bus
    event_types = (
        TaskCreated,
        TaskProfileUpdated,
        TaskHierarchyChanged,
        TaskStatusChanged,
        TaskProgressChanged,
        TaskScheduleChanged,
        TaskRemoved,
        TaskAssignmentChanged,
        TaskDependencyChanged,
    )
    handlers = [
        next(handler for handler in bus._handlers[event_type] if handler.__name__ == "handle_task_event")
        for event_type in event_types
    ]
    assert all(
        sum(handler.__name__ == "handle_task_event" for handler in bus._handlers[event_type]) == 1
        for event_type in event_types
    )
    assert all(handler is handlers[0] for handler in handlers)
    scoped_session = task_uow._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_timesheet_instance_and_invalidation_subscription_are_shared(services) -> None:
    timesheet = services["timesheet_service"]
    assert services["time_service"] is timesheet
    assert services["task_service"]._timesheet_service is timesheet
    bus = services["project_service"]._uow_factory._post_commit_bus
    assert sum(
        handler.__name__ == "handle_timesheet_period_event"
        for handler in bus._handlers[TimesheetPeriodStatusChanged]
    ) == 1
