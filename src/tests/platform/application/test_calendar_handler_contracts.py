from __future__ import annotations

import inspect
from datetime import time
from unittest.mock import MagicMock

import pytest

from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
)
from src.core.platform.application.time_management.calendar.assignment.commands.calendar_assignment_commands import (
    CalendarAssignmentCommandHandler,
)
from src.core.platform.application.time_management.calendar.assignment.queries.calendar_assignment_queries import (
    CalendarAssignmentQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.shift_pattern_commands import (
    ShiftPatternCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.shift_pattern_queries import (
    ShiftPatternQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.working_rule_queries import (
    WorkingRuleQueryHandler,
)


@pytest.mark.parametrize(
    ("command_type", "query_type", "command_operations", "query_operations"),
    [
        (
            PlatformCalendarCommandHandler,
            PlatformCalendarQueryHandler,
            [
                "create_calendar",
                "update_calendar",
                "set_organization_default_calendar",
                "delete_calendar",
                "ensure_global_calendar",
            ],
            [
                "list_calendars",
                "get_calendar",
                "get_calendars_by_ids",
                "get_default_calendar",
            ],
        ),
        (
            CalendarAssignmentCommandHandler,
            CalendarAssignmentQueryHandler,
            [
                "assign_site_calendar",
                "remove_site_assignment",
                "assign_department_calendar",
                "remove_department_assignment",
                "assign_employee_calendar",
                "remove_employee_assignment",
                "assign_project_calendar",
                "remove_project_assignment",
                "assign_resource_calendar",
                "remove_resource_assignment",
            ],
            [
                "get_site_calendar",
                "list_site_assignments",
                "get_department_calendar",
                "list_department_assignments",
                "get_employee_calendar",
                "list_employee_assignments",
                "get_project_calendar",
                "get_resource_calendar",
                "list_calendar_assignments",
            ],
        ),
        (
            CalendarExceptionCommandHandler,
            CalendarExceptionQueryHandler,
            [
                "add_exception",
                "update_exception",
                "delete_exception",
                "add_site_exception",
                "add_department_exception",
                "add_employee_exception",
                "add_resource_exception",
            ],
            ["list_exceptions"],
        ),
        (
            WorkingRuleCommandHandler,
            WorkingRuleQueryHandler,
            ["save_rule", "delete_rule", "seed_standard_week"],
            ["list_rules"],
        ),
        (
            ShiftPatternCommandHandler,
            ShiftPatternQueryHandler,
            [
                "create_shift_pattern",
                "update_shift_pattern",
                "delete_shift_pattern",
                "set_day",
                "delete_day",
            ],
            ["list_shift_patterns", "get_shift_pattern", "list_days"],
        ),
        (
            RecurringEventCommandHandler,
            RecurringEventQueryHandler,
            ["add_recurring_event", "update_recurring_event", "delete_recurring_event"],
            ["list_recurring_events", "expand_occurrences"],
        ),
    ],
)
def test_handlers_expose_only_their_side_of_the_feature(
    command_type, query_type, command_operations, query_operations
):
    assert "session" not in inspect.signature(query_type).parameters
    for operation in command_operations:
        assert callable(getattr(command_type, operation))
        assert not hasattr(query_type, operation)
    for operation in query_operations:
        assert callable(getattr(query_type, operation))
        assert not hasattr(command_type, operation)
    for handler_type in (command_type, query_type):
        parameters = inspect.signature(handler_type).parameters.values()
        assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters)


def _working_rule_commands():
    session = MagicMock()
    rules = MagicMock()
    rules.get_for_weekday.return_value = None
    invalidated = MagicMock()
    handler = WorkingRuleCommandHandler(
        session=session,
        calendar_repo=MagicMock(),
        rule_repo=rules,
        user_session=MagicMock(),
        on_calendar_data_changed=invalidated,
    )
    return handler, session, rules, invalidated


def test_staged_rule_write_flushes_without_committing_or_invalidating():
    handler, session, rules, invalidated = _working_rule_commands()
    saved = handler.save_rule("calendar", 0, hours_override=8, commit=False)
    rules.save.assert_called_once_with(saved)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
    invalidated.assert_not_called()


def test_standard_week_commits_once_before_invalidating():
    handler, session, rules, invalidated = _working_rule_commands()
    calls = []
    session.commit.side_effect = lambda: calls.append("commit")
    invalidated.side_effect = lambda: calls.append("invalidate")
    saved = handler.seed_standard_week(
        "calendar", start_time=time(8), end_time=time(17)
    )
    assert len(saved) == 7
    assert rules.save.call_count == 7
    assert session.flush.call_count == 7
    assert calls == ["commit", "invalidate"]
    session.rollback.assert_not_called()


def test_standard_week_failure_rolls_back_without_invalidating():
    handler, session, rules, invalidated = _working_rule_commands()
    rules.save.side_effect = [None, RuntimeError("write failed")]
    with pytest.raises(RuntimeError, match="write failed"):
        handler.seed_standard_week("calendar", start_time=time(8), end_time=time(17))
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    invalidated.assert_not_called()


def test_failed_rule_commit_does_not_invalidate_resolver():
    handler, session, _, invalidated = _working_rule_commands()
    session.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError, match="commit failed"):
        handler.save_rule("calendar", 0, hours_override=8)
    invalidated.assert_not_called()


def test_calendar_builder_exposes_explicit_handlers_and_shared_invalidation():
    from dataclasses import fields

    from src.core.platform.infrastructure.composition.dependencies.time.calendar import (
        build_calendar_dependencies,
    )

    tenant_context = MagicMock()
    tenant_context.get_active_organization.return_value = None
    tenant_context.get_active_organization_id.return_value = "organization"
    dependencies = build_calendar_dependencies(
        session=MagicMock(),
        repositories=MagicMock(),
        user_session=MagicMock(),
        tenant_context_service=tenant_context,
        activity_service=MagicMock(),
    )
    keys = {field.name for field in fields(dependencies)}
    for prefix in (
        "platform_calendar",
        "calendar_assignment",
        "working_rule",
        "calendar_exception",
        "recurring_event",
        "shift_pattern",
    ):
        assert prefix + "_commands" in keys
        assert prefix + "_queries" in keys
        assert prefix + "_service" not in keys
        assert not hasattr(getattr(dependencies, prefix + "_queries"), "_session")
    for prefix in ("working_rule", "recurring_event", "shift_pattern"):
        callback = getattr(dependencies, prefix + "_commands")._on_calendar_data_changed
        assert callback.__self__ is dependencies.platform_calendar_resolver
    assert (
        dependencies.global_calendar_shim._resolver
        is dependencies.platform_calendar_resolver
    )
