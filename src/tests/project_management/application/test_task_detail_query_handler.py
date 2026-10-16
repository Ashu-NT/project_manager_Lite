from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.common.exceptions import BusinessRuleError


def test_task_detail_batch_lookup_uses_one_scoped_repository_call(services, monkeypatch) -> None:
    project = services["project_create"].create_project(ProjectCreateCommand(name="Batch task lookup"))
    tasks = [services["task_lifecycle_commands"].create_task(project.id, name) for name in ("Task A", "Task B")]
    detail = services["task_detail_query"]
    read = Mock(wraps=detail._task_repo.list_by_ids)
    monkeypatch.setattr(detail._task_repo, "list_by_ids", read)
    result = detail.list_tasks_by_ids([tasks[0].id, tasks[1].id, tasks[0].id])
    assert {task.id for task in result} == {task.id for task in tasks}
    read.assert_called_once_with([tasks[0].id, tasks[1].id])


def test_task_detail_batch_lookup_preserves_project_denial(services, monkeypatch) -> None:
    project = services["project_create"].create_project(ProjectCreateCommand(name="Denied batch lookup"))
    task = services["task_lifecycle_commands"].create_task(project.id, "Restricted")
    detail = services["task_detail_query"]
    deny = Mock(side_effect=BusinessRuleError("Project access denied.", code="PERMISSION_DENIED"))
    monkeypatch.setattr(
        "src.core.modules.project_management.application.tasks.queries.task_detail_page.require_project_permission", deny
    )
    with pytest.raises(BusinessRuleError, match="Project access denied"):
        detail.list_tasks_by_ids([task.id])


def test_task_detail_pages_keep_server_order_filters_and_bounded_pages(services) -> None:
    detail = services["task_detail_query"]
    project = services['project_create'].create_project(ProjectCreateCommand(name="Task detail query project"))
    predecessor = services['task_lifecycle_commands'].create_task(project.id, "Predecessor")
    task = services['task_lifecycle_commands'].create_task(project.id, "Target")
    successor = services['task_lifecycle_commands'].create_task(project.id, "Successor")
    zed = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Zed Resource"))
    ada = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Ada Resource"))
    services['task_assignment_commands'].assign_resource(task.id, zed.id, allocation_percent=25)
    services['task_assignment_commands'].assign_resource(task.id, ada.id, allocation_percent=25)
    services['task_dependency_commands'].add_dependency(predecessor.id, task.id, DependencyType.FINISH_TO_START)
    services['task_dependency_commands'].add_dependency(task.id, successor.id, DependencyType.FINISH_TO_START)

    first = detail.query_task_assignments_page(
        task.id, page=1, page_size=1, sort_key="resourceName", sort_direction="asc"
    )
    last = detail.query_task_assignments_page(
        task.id, page=99, page_size=1, sort_key="resourceName", sort_direction="asc"
    )
    descending = detail.query_task_assignments_page(
        task.id, page=1, page_size=1, sort_key="resourceName", sort_direction="desc"
    )
    assert first.filtered_total == last.filtered_total == descending.filtered_total == 2
    assert (first.items[0].resource_name, last.items[0].resource_name) == (
        "Ada Resource",
        "Zed Resource",
    )
    assert last.page == 2
    assert descending.items[0].resource_name == "Zed Resource"

    before = detail.query_task_dependencies_page(task.id, direction="predecessor")
    after = detail.query_task_dependencies_page(task.id, direction="successor")
    assert before.filtered_total == after.filtered_total == 1
    assert before.items[0].linked_task_id == predecessor.id
    assert after.items[0].linked_task_id == successor.id
    assert detail.query_task_activity_page(task.id, page_size=1).page_size == 1


def test_task_detail_scope_denial_stops_before_reader(services, monkeypatch) -> None:
    project = services['project_create'].create_project(ProjectCreateCommand(name="Task detail scope project"))
    task = services['task_lifecycle_commands'].create_task(project.id, "Scoped task")
    detail = services["task_detail_query"]
    reader = detail._task_workspace_reader
    read_page = Mock(side_effect=AssertionError("reader reached after denial"))
    monkeypatch.setattr(reader, "read_assignments_page", read_page)

    def deny_project(*_args, **_kwargs) -> None:
        raise BusinessRuleError("Project access denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.modules.project_management.application.tasks.queries.task_detail_page.require_project_permission",
        deny_project,
    )
    with pytest.raises(BusinessRuleError, match="Project access denied"):
        detail.query_task_assignments_page(task.id)
    read_page.assert_not_called()


def test_task_read_handlers_share_the_composed_workspace_reader(services) -> None:
    assert (
        services["task_detail_query"]._task_workspace_reader
        is services["task_workspace_query"]._task_workspace_reader
    )
