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


def test_project_desktop_consumers_reuse_composed_handlers(services):
    from src.application.runtime.desktop_api_registry import build_desktop_api_registry

    registry = build_desktop_api_registry(services)
    projects = registry.project_management_projects
    assert projects._project_create is services["project_create"]
    assert projects._project_update is services["project_update"]
    assert projects._project_status is services["project_status"]
    assert projects._project_deletion is services["project_deletion"]
    assert registry.project_management_tasks._project_service is services["project_query"]
    assert registry.project_management_timesheets._project_service is services["project_query"]
    assert registry.project_management_scheduling._project_service is services["project_query"]


def test_project_events_share_one_post_commit_handler(services) -> None:
    bus = services['project_create']._uow_factory._post_commit_bus

    assert bus is services['task_uow_scope']._factory._post_commit_bus
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
    scoped_session = services['project_create']._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_register_uses_shared_bus_and_one_invalidation_handler(services, session) -> None:
    project_bus = services['project_create']._uow_factory._post_commit_bus
    register_uow = services["register_lifecycle_commands"]._uow_factory
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
    task_uow = services['task_uow_scope']._factory
    bus = services['project_create']._uow_factory._post_commit_bus
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


def test_project_query_capability_reuses_the_composed_handler(services) -> None:
    assert services["data_import_service"]._project_query is services["project_query"]


def test_timesheet_instance_and_invalidation_subscription_are_shared(services) -> None:
    assert services["time_entry_commands"] is services["time_entry_commands"]
    assert services["time_entry_queries"] is services["time_entry_queries"]
    assert services["task_time_entries"]._time_queries is services["time_entry_queries"]
    bus = services['project_create']._uow_factory._post_commit_bus
    assert sum(
        handler.__name__ == "handle_timesheet_period_event"
        for handler in bus._handlers[TimesheetPeriodStatusChanged]
    ) == 1


def test_resource_readers_clock_uow_and_events_preserve_identity(services, session) -> None:
    resource = services["resource_query"]
    assert resource._resource_catalog_reader is resource._resource_inspector_reader
    assert resource._resource_catalog_reader is resource._resource_summary_reader
    context_query = services["resource_context_query"]
    capability_query = services["resource_capability_query"]
    context_reader = context_query._resource_projects_reader
    assert context_reader is context_query._resource_assignments_reader
    assert context_reader is context_query._resource_activity_reader
    assert context_reader is capability_query._resource_capability_reader

    bus = services['project_create']._uow_factory._post_commit_bus
    master_commands = services["resource_master_commands"]
    capability_commands = services["resource_capability_commands"]
    assert master_commands._uow_factory._post_commit_bus is bus
    assert capability_commands._uow_factory is master_commands._uow_factory
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
    scoped_session = master_commands._uow_factory._session_factory()
    try:
        assert scoped_session is not session
        assert scoped_session.bind is session.bind
    finally:
        scoped_session.close()


def test_scheduling_and_baseline_keep_shared_engine_and_ambient_uow(services, session) -> None:
    engine = services["scheduling_engine"]
    baseline = services['baseline_commands']
    assert baseline._sched is engine
    assert (
        engine._project_calendar_adapter
        is services["portfolio_executive_query"]._heatmap_calculator._project_calendar_adapter
    )
    assert services['baseline_commands']._session is session
    assert baseline._uow_factory()._session is session

    bus = services['project_create']._uow_factory._post_commit_bus
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
    collaboration = services["collaboration_comment_commands"]
    bus = services['project_create']._uow_factory._post_commit_bus
    assert collaboration._uow_factory._post_commit_bus is bus
    # Every collaboration write handler shares the one collaboration UoW factory.
    for key in ("collaboration_comment_engagement", "collaboration_presence_commands"):
        assert services[key]._uow_factory is collaboration._uow_factory
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


def test_portfolio_reuses_calendar_with_one_event_handler(services, session) -> None:
    portfolio = services["portfolio_intake_commands"]
    calculator = services["portfolio_executive_query"]._heatmap_calculator
    assert calculator._project_calendar_adapter is services["scheduling_engine"]._project_calendar_adapter
    assert services["portfolio_dependency_query"]._heatmap_calculator is calculator
    bus = services['project_create']._uow_factory._post_commit_bus
    assert portfolio._uow_factory._post_commit_bus is bus
    # One portfolio UoW factory and one shared scope/scoring policy across handlers.
    for key in (
        "portfolio_template_commands",
        "portfolio_scenario_commands",
        "portfolio_dependency_commands",
    ):
        assert services[key]._uow_factory is portfolio._uow_factory
        assert services[key]._policy is portfolio._policy
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
    kpi = services["project_kpi_report"]
    earned_value = services["earned_value_report"]
    cost_breakdown = services["cost_breakdown_report"]
    assert kpi._scheduling_engine is services["scheduling_engine"]
    # One shared cost policy (single reporting financial authority) and one
    # shared access policy across every report builder.
    cost_policy = kpi._cost_policy
    assert cost_policy._rate_resolver is services["rate_card_resolver"]
    for builder in (earned_value, cost_breakdown, services["profitability_report"]):
        assert builder._cost_policy is cost_policy
    for builder in (
        earned_value,
        cost_breakdown,
        services["baseline_compare_report"],
        services["schedule_variance_report"],
        services["profitability_report"],
        services["labor_report"],
    ):
        assert builder._access is kpi._access
    assert services["schedule_variance_report"]._critical_path is kpi
    assert services["finance_performance_query"]._earned_value_authority is earned_value

    dashboard = services["project_dashboard_query"]
    assert dashboard._kpi_report is kpi
    assert dashboard._cost_sources is cost_breakdown
    assert dashboard._evm._earned_value is earned_value
    assert dashboard._task_lookup is services['task_lookup_query']
    assert dashboard._resources is services["resource_query"]
    assert dashboard._registers._registers is services["register_query"]
    portfolio = services["portfolio_dashboard_query"]
    assert portfolio._reporting is kpi
    assert portfolio._projects is services["project_query"]
    assert portfolio._resources is services["resource_query"]
    assert portfolio._task_lookup is services['task_lookup_query']


def test_resource_planning_and_imports_keep_shared_dependencies(services) -> None:
    assert (
        services["project_resource_commands"]._shared_uow_factory
        is services['project_deletion']._shared_uow_factory
    )
    availability = services["resource_availability_service"]
    assert services["resource_capacity_calculator"]._availability is availability
    assert services["resource_workload_query"]._availability is availability
    imports = services["data_import_service"]
    assert imports._project_query is services["project_query"]
    assert imports._project_create is services["project_create"]
    assert imports._project_update is services["project_update"]
    assert imports._project_status is services["project_status"]
    assert imports._task_capabilities.lookup is services['task_lookup_query']
    assert services["task_lookup_query"] is services['task_lookup_query']
    assert services["task_detail_query"] is services['task_detail_query']
    assert (
        services["task_dependency_diagnostics"]
        is services['task_dependency_commands']._diagnostics_handler
    )
    assert services["task_assignment_commands"] is services['task_assignment_commands']
    assert imports._task_capabilities.lifecycle is services['task_lifecycle_commands']
    assert imports._resource_query is services["resource_query"]
    assert imports._resource_master_commands is services["resource_master_commands"]
