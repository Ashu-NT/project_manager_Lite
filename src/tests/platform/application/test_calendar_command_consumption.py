"""Calendar DTO ownership and direct Desktop-to-application contracts."""

from __future__ import annotations

import inspect
from datetime import date
from importlib import import_module
from unittest.mock import MagicMock

import pytest

from src.core.platform.api.desktop.time_management.calendar import platform_calendar
from src.core.platform.api.desktop.time_management.calendar.platform_calendar import (
    PlatformCalendarDesktopApi,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.dto.commands.working_rules import (
    WorkingRuleSaveCommand,
)

WRITE_OPERATIONS = [
    ("create_calendar", "platform_calendar_commands", "create_calendar"),
    ("update_calendar", "platform_calendar_commands", "update_calendar"),
    ("save_working_rule", "working_rule_commands", "save_rule"),
    ("add_exception", "calendar_exception_commands", "add_exception"),
    ("update_exception", "calendar_exception_commands", "update_exception"),
    ("add_recurring_event", "recurring_event_commands", "add_recurring_event"),
    ("update_recurring_event", "recurring_event_commands", "update_recurring_event"),
    ("create_shift_pattern", "shift_pattern_commands", "create_shift_pattern"),
    ("update_shift_pattern", "shift_pattern_commands", "update_shift_pattern"),
    ("set_shift_pattern_day", "shift_pattern_commands", "set_day"),
    ("assign_site_calendar", "calendar_assignment_commands", "assign_site_calendar"),
    (
        "assign_department_calendar",
        "calendar_assignment_commands",
        "assign_department_calendar",
    ),
    (
        "assign_employee_calendar",
        "calendar_assignment_commands",
        "assign_employee_calendar",
    ),
    (
        "assign_project_calendar",
        "calendar_assignment_commands",
        "assign_project_calendar",
    ),
    (
        "assign_resource_calendar",
        "calendar_assignment_commands",
        "assign_resource_calendar",
    ),
]


@pytest.mark.parametrize(
    ("api_method", "dependency", "handler_method"), WRITE_OPERATIONS
)
def test_desktop_passes_the_original_command_to_the_injected_handler(
    monkeypatch, api_method, dependency, handler_method
):
    dependencies = {
        name: MagicMock()
        for name in inspect.signature(PlatformCalendarDesktopApi).parameters
    }
    api = PlatformCalendarDesktopApi(**dependencies)
    output = object()
    for serializer in (
        "_serialize_calendar",
        "_serialize_rule",
        "_serialize_exception",
        "_serialize_recurring_event",
        "_serialize_shift_pattern",
        "_serialize_shift_day",
    ):
        monkeypatch.setattr(platform_calendar, serializer, lambda value: output)
    monkeypatch.setattr(api, "_serialize_assignment", lambda *args, **kwargs: output)
    command = object()

    result = getattr(api, api_method)(command)

    assert result.ok, result.error
    assert result.data is output
    getattr(dependencies[dependency], handler_method).assert_called_once_with(command)


@pytest.mark.parametrize("commit", [True, False])
def test_zero_hour_override_and_participant_transaction_are_preserved(commit):
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

    result = handler.save_rule(
        WorkingRuleSaveCommand(
            calendar_id="calendar",
            weekday=0,
            hours_override=0.0,
            effective_from=date(2026, 1, 1),
            priority=0,
            commit=commit,
        )
    )

    assert result.hours_override == 0.0
    assert result.effective_from == date(2026, 1, 1)
    assert result.priority == 0
    assert session.commit.call_count == int(commit)
    assert session.flush.call_count == int(not commit)
    assert invalidated.call_count == int(commit)


@pytest.mark.parametrize(
    ("api_method", "resolver_method"),
    [
        ("resolve_calendar_context", "resolve_calendar_context"),
        ("resolve_calendar_range", "resolve_range"),
        ("resolve_effective_calendar", "resolve_effective_calendar"),
        ("calculate_working_days", "calculate_working_days"),
        ("calculate_resource_capacity", "calculate_resource_capacity"),
    ],
)
def test_desktop_passes_query_inputs_directly_to_the_existing_resolver(
    api_method, resolver_method
):
    dependencies = {
        name: MagicMock()
        for name in inspect.signature(PlatformCalendarDesktopApi).parameters
    }
    api = PlatformCalendarDesktopApi(**dependencies)
    command = object()

    result = getattr(api, api_method)(command)

    assert result.ok, result.error
    expected = (
        {"calculator": dependencies["capacity_calculator"]}
        if api_method == "calculate_resource_capacity"
        else {}
    )
    getattr(dependencies["resolver"], resolver_method).assert_called_once_with(
        command, **expected
    )


@pytest.mark.parametrize(
    ("package", "old_name"),
    [
        ("dto", "CalendarCreateCommand"),
        ("definitions.dto", "WorkingRuleSaveCommand"),
        ("assignment.dto", "SiteCalendarAssignCommand"),
        ("capacity.dto", "ResolveContextCommand"),
    ],
)
def test_dto_packages_do_not_offer_old_flat_path_reexports(package, old_name):
    module = import_module(
        "src.core.platform.application.time_management.calendar." + package
    )
    assert not hasattr(module, old_name)
