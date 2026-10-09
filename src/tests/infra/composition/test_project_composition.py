from __future__ import annotations

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentReactionChanged,
    TaskCommentReadStateChanged,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioIntakeItemChanged,
    PortfolioProjectDependencyChanged,
    PortfolioScenarioChanged,
    PortfolioScoringTemplateChanged,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
    ProjectProfileUpdated,
    ProjectRemoved,
    ProjectStatusChanged,
)
from src.core.modules.project_management.application.resources.catalog.resource_capability_events import (
    ResourceCapabilityChanged,
)
from src.core.modules.project_management.application.resources.catalog.resource_master_events import (
    ResourceMasterChanged,
)
from src.core.modules.project_management.application.resources.project_resources.project_resource_events import (
    ProjectResourceAssignmentChanged,
)
from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChanged,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineApproved,
    ProjectBaselineCreated,
    ProjectBaselineDeleted,
    ProjectBaselineRejected,
    ProjectBaselineSubmitted,
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
from src.core.platform.domain.master_data.employee.events import EmployeeProfileUpdated


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


def test_resource_readers_clock_uow_and_events_preserve_identity(services, session) -> None:
    resource = services["resource_service"]
    assert resource._resource_catalog_reader is resource._resource_inspector_reader
    assert resource._resource_catalog_reader is resource._resource_summary_reader
    assert resource._resource_projects_reader is resource._resource_assignments_reader
    assert resource._resource_projects_reader is resource._resource_activity_reader
    assert resource._resource_projects_reader is resource._resource_capability_reader
    assert resource._clock is services["rate_card_resolver"]._clock

    bus = services["project_service"]._uow_factory._post_commit_bus
    assert resource._uow_factory._post_commit_bus is bus
    for event_type, handler_name in (
        (ResourceMasterChanged, "handle_resource_master_event"),
        (ResourceCapabilityChanged, "handle_resource_capability_event"),
    ):
        assert sum(handler.__name__ == handler_name for handler in bus._handlers[event_type]) == 1
    assert sum(
        "build_linked_employee_resource_view_invalidation_handler.<locals>.handle"
        in handler.__qualname__
        for handler in bus._handlers[EmployeeProfileUpdated]
    ) == 1
    scoped_session = resource._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_scheduling_and_baseline_keep_shared_engine_and_ambient_uow(services, session) -> None:
    engine = services["scheduling_engine"]
    baseline = services["baseline_service"]
    assert baseline._sched is engine
    assert engine._project_calendar_adapter is services["portfolio_service"]._project_calendar_adapter
    assert baseline._session is session
    assert baseline._uow_factory()._session is session

    bus = services["project_service"]._uow_factory._post_commit_bus
    event_types = (
        ProjectBaselineCreated,
        ProjectBaselineSubmitted,
        ProjectBaselineApproved,
        ProjectBaselineRejected,
        ProjectBaselineDeleted,
    )
    handlers = [
        next(
            handler
            for handler in bus._handlers[event_type]
            if handler.__name__ == "handle_baseline_event"
        )
        for event_type in event_types
    ]
    assert all(
        sum(handler.__name__ == "handle_baseline_event" for handler in bus._handlers[event_type]) == 1
        for event_type in event_types
    )
    assert all(handler is handlers[0] for handler in handlers)


def test_collaboration_keeps_fresh_uow_and_one_comment_handler(services, session) -> None:
    collaboration = services["collaboration_service"]
    bus = services["project_service"]._uow_factory._post_commit_bus
    assert collaboration._uow_factory._post_commit_bus is bus
    event_types = (TaskCommentChanged, TaskCommentReactionChanged, TaskCommentReadStateChanged)
    handlers = [
        next(
            handler
            for handler in bus._handlers[event_type]
            if handler.__name__ == "handle_task_comment_event"
        )
        for event_type in event_types
    ]
    assert all(
        sum(
            handler.__name__ == "handle_task_comment_event"
            for handler in bus._handlers[event_type]
        ) == 1
        for event_type in event_types
    )
    assert all(handler is handlers[0] for handler in handlers)
    scoped_session = collaboration._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_portfolio_reuses_calendar_and_rate_with_one_event_handler(services, session) -> None:
    portfolio = services["portfolio_service"]
    assert portfolio._project_calendar_adapter is services["scheduling_engine"]._project_calendar_adapter
    assert portfolio._rate_resolver is services["rate_card_resolver"]
    bus = services["project_service"]._uow_factory._post_commit_bus
    assert portfolio._uow_factory._post_commit_bus is bus
    event_types = (
        PortfolioIntakeItemChanged,
        PortfolioScenarioChanged,
        PortfolioScoringTemplateChanged,
        PortfolioProjectDependencyChanged,
    )
    handlers = [
        next(
            handler
            for handler in bus._handlers[event_type]
            if handler.__name__ == "handle_portfolio_event"
        )
        for event_type in event_types
    ]
    assert all(
        sum(handler.__name__ == "handle_portfolio_event" for handler in bus._handlers[event_type]) == 1
        for event_type in event_types
    )
    assert all(handler is handlers[0] for handler in handlers)
    scoped_session = portfolio._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_reporting_and_dashboard_reuse_authoritative_services(services) -> None:
    reporting = services["reporting_service"]
    dashboard = services["dashboard_service"]
    assert reporting._scheduling_engine is services["scheduling_engine"]
    assert reporting._rate_resolver is services["rate_card_resolver"]
    assert dashboard._reporting is reporting
    assert dashboard._tasks is services["task_service"]
    assert dashboard._projects is services["project_service"]
    assert dashboard._resources is services["resource_service"]
    assert dashboard._registers is services["register_service"]


def test_resource_planning_and_imports_keep_shared_dependencies(services) -> None:
    assert (
        services["project_resource_service"]._shared_uow_factory
        is services["project_service"]._shared_uow_factory
    )
    availability = services["resource_availability_service"]
    assert services["resource_capacity_calculator"]._availability is availability
    assert services["resource_workload_service"]._availability is availability
    imports = services["data_import_service"]
    assert imports._project_service is services["project_service"]
    assert imports._task_service is services["task_service"]
    assert imports._resource_service is services["resource_service"]
