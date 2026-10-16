from dataclasses import FrozenInstanceError
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.application.dashboard.models.report_models import (
    ResourceLoadRow,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidationResult,
    ConstraintViolation,
)
from src.core.modules.project_management.application.scheduling.dto.commands.dependencies import (
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
)
from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.domain.enums import (
    ConstraintType,
    DependencyType,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.platform.common.exceptions import ConfigurationError, ValidationError


def test_resource_load_returns_canonical_report_result_without_cloning() -> None:
    rows = [ResourceLoadRow("resource-1", "Ada", 120.0, 2, 80.0, 150.0)]
    report = Mock()
    report.get_resource_load_summary.return_value = rows
    api = ProjectManagementSchedulingDesktopApi(project_kpi_report=report)

    assert api.list_resource_load(" project-1 ") is rows
    report.get_resource_load_summary.assert_called_once_with("project-1")
    assert not hasattr(rows[0], "utilization_label")
    assert api.list_resource_load(" ") == []
    report.get_resource_load_summary.assert_called_once()
    assert ProjectManagementSchedulingDesktopApi().list_resource_load("project-1") == []


def test_resource_load_does_not_hide_authorization_errors() -> None:
    report = Mock()
    error = ValidationError("Access denied", code="PROJECT_ACCESS_DENIED")
    report.get_resource_load_summary.side_effect = error
    api = ProjectManagementSchedulingDesktopApi(project_kpi_report=report)

    with pytest.raises(ValidationError) as raised:
        api.list_resource_load("project-1")
    assert raised.value is error


def test_constraints_return_canonical_results_after_read_only_leaf_validation() -> None:
    violation = ConstraintViolation(
        "leaf", "Execution", ConstraintType.DEADLINE,
        date(2026, 5, 4), date(2026, 5, 6), "Deadline exceeded", 2,
    )
    summary = SimpleNamespace(id="summary", parent_task_id=None)
    leaf = SimpleNamespace(id="leaf", parent_task_id="summary")
    query = Mock()
    query.list_tasks_for_project.return_value = [summary, leaf]
    engine = Mock()
    schedule = {"leaf": object()}
    engine.recalculate_project_schedule.return_value = schedule
    validator = Mock()
    validator.validate.return_value = ConstraintValidationResult([violation])
    api = ProjectManagementSchedulingDesktopApi(
        task_lookup_query=query, scheduling_engine=engine, constraint_validator=validator,
    )

    result = api.list_constraint_violations(" project-1 ")

    assert result == (violation,)
    assert result[0] is violation
    assert not hasattr(result[0], "severity_label")
    engine.recalculate_project_schedule.assert_called_once_with("project-1", persist=False)
    query.list_tasks_for_project.assert_called_once_with("project-1")
    validator.validate.assert_called_once_with({"leaf": leaf}, schedule)
    with pytest.raises(FrozenInstanceError):
        setattr(violation, "message", "Changed")


@pytest.mark.parametrize("constraint_type", list(ConstraintType))
def test_constraint_severity_preserves_application_policy(constraint_type: ConstraintType) -> None:
    violation = ConstraintViolation(
        "task-1", "Task", constraint_type,
        date(2026, 5, 4), date(2026, 5, 6), "Mismatch", 2,
    )
    expected_hard = constraint_type in {
        ConstraintType.MUST_START_ON, ConstraintType.MUST_FINISH_ON,
        ConstraintType.START_NO_LATER_THAN, ConstraintType.FINISH_NO_LATER_THAN,
        ConstraintType.DEADLINE,
    }
    result = ConstraintValidationResult([violation])

    assert violation.is_hard is expected_hard
    assert result.hard_violations == ([violation] if expected_hard else [])


def test_leveling_returns_and_applies_the_identical_immutable_proposal() -> None:
    proposal = LevelingProposal("project-1", "snapshot-1", True, 1, 0, (), (), None, None, False, (), ())
    commands = Mock()
    commands.build_resource_leveling_preview.return_value = proposal
    engine = Mock()
    engine.recalculate_project_schedule.return_value = {}
    api = ProjectManagementSchedulingDesktopApi(task_leveling_commands=commands, scheduling_engine=engine)

    assert api.preview_resource_leveling(" project-1 ") is proposal
    assert not hasattr(proposal, "project_finish_before_label")
    with pytest.raises(FrozenInstanceError):
        setattr(proposal, "schedule_fingerprint", "changed")
    assert api.apply_resource_leveling("project-1") == ()
    commands.apply_resource_leveling_plan.assert_called_once_with("project-1", proposal)
    assert commands.apply_resource_leveling_plan.call_args.args[1] is proposal
    engine.recalculate_project_schedule.assert_called_once_with("project-1", persist=False)


def test_dependency_commands_return_the_canonical_response_without_extra_reads() -> None:
    response = TaskDependencyResponseDto("edge-1", "before", "after", DependencyType.FINISH_TO_START, 2, 1)
    commands = Mock()
    commands.add_dependency.return_value = response
    commands.update_dependency.return_value = response
    api = ProjectManagementSchedulingDesktopApi(task_dependency_commands=commands)
    create = SchedulingDependencyCreateCommand("after", "before", "PREDECESSOR", "FS", 2)
    update = SchedulingDependencyUpdateCommand("edge-1", "FS", 2, 1)

    assert api.create_dependency(create) is response
    assert api.update_dependency(update) is response
    commands.add_dependency.assert_called_once_with(create)
    commands.update_dependency.assert_called_once_with(update)


def test_dependency_reads_return_the_canonical_query_result_without_cloning() -> None:
    detail = Mock()
    detail.get_task.return_value = SimpleNamespace(id="task-1", project_id="project-1")
    query = Mock()
    rows = (object(),)
    query.query_dependency_responses.return_value = rows
    api = ProjectManagementSchedulingDesktopApi(task_detail_query=detail, task_dependency_query=query)

    assert api.list_dependencies(" task-1 ") is rows
    query.query_dependency_responses.assert_called_once_with("task-1")


def test_schedule_returns_immutable_facts_and_preserves_recalculation_mode() -> None:
    task = Task(id="task-1", project_id="project-1", name="Task", duration_days=2)
    info = SimpleNamespace(
        task=task, earliest_start=date(2026, 5, 4), earliest_finish=date(2026, 5, 5),
        latest_start=date(2026, 5, 6), latest_finish=date(2026, 5, 7),
        total_float_days=2, is_critical=False, is_infeasible=False, deadline=None, late_by_days=None,
    )
    engine = Mock()
    engine.recalculate_project_schedule.return_value = {task.id: info}
    api = ProjectManagementSchedulingDesktopApi(scheduling_engine=engine)

    row = api.list_schedule(" project-1 ")[0]

    assert row.start_date == info.earliest_start
    assert row.finish_date == info.earliest_finish
    assert row.total_float_days == 2
    assert not hasattr(row, "status_label")
    assert not hasattr(row, "constraint_type_label")
    with pytest.raises(FrozenInstanceError):
        setattr(row, "name", "Changed")
    task.name = "Domain changed later"
    assert row.name == "Task"
    engine.recalculate_project_schedule.assert_called_once_with("project-1", persist=False)
    api.recalculate_schedule("project-1")
    assert engine.recalculate_project_schedule.call_args.kwargs == {"persist": True}


def test_schedule_requires_the_canonical_engine_without_a_plain_task_fallback() -> None:
    with pytest.raises(ConfigurationError):
        ProjectManagementSchedulingDesktopApi().list_schedule("project-1")


def test_project_dependencies_are_mapped_once_with_one_complete_edge_read() -> None:
    before = Task(id="before", project_id="project-1", name="Before")
    after = Task(id="after", project_id="project-1", name="After")
    dependencies = [
        TaskDependency(
            id=f"edge-{kind.value}", predecessor_task_id=before.id, successor_task_id=after.id,
            dependency_type=kind, lag_days=2,
        )
        for kind in DependencyType
    ]
    query = Mock()
    query.list_dependencies_for_project.return_value = dependencies
    lookup = Mock()
    lookup.list_tasks_for_project.return_value = [after, before]
    api = ProjectManagementSchedulingDesktopApi(task_dependency_query=query, task_lookup_query=lookup)

    rows = api.list_project_dependencies(" project-1 ")

    assert [row.dependency_type.value for row in rows] == ["FF", "FS", "SF", "SS"]
    assert all(isinstance(row, TaskDependencyResponseDto) for row in rows)
    assert all(not hasattr(row, "dependency_type_label") for row in rows)
    assert {row.id for row in rows} == {edge.id for edge in dependencies}
    query.list_dependencies_for_project.assert_called_once_with("project-1")
    lookup.list_tasks_for_project.assert_called_once_with("project-1")
