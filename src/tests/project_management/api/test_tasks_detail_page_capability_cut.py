from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.tasks.commands.dependency_commands import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.common.exceptions import BusinessRuleError


def test_task_detail_pages_use_composed_query_handler(services) -> None:
    project = services["project_service"].create_project("Task Detail Pages")
    tasks = services["task_service"]
    predecessor = tasks.create_task(project.id, "Predecessor")
    task = tasks.create_task(project.id, "Delivery")
    resource = services["resource_service"].create_resource("Planner")
    tasks.assign_resource(task.id, resource.id, allocation_percent=50)
    tasks.add_dependency(predecessor.id, task.id, DependencyType.FINISH_TO_START)
    api = build_project_management_tasks_desktop_api(
        task_detail_query=services["task_detail_query"],
        module_catalog_service=services["module_catalog_service"],
    )

    assert api.list_assignments_page(task.id).filtered_total == 1
    assert api.list_dependencies_page(task.id).filtered_total == 1
    assert api.list_task_activity_page(task.id).page == 1


@pytest.mark.parametrize(
    "method",
    ("list_assignments_page", "list_dependencies_page", "list_task_activity_page"),
)
def test_task_detail_pages_check_module_before_query_handler(method: str) -> None:
    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    query = SimpleNamespace(
        query_task_assignments_page=lambda *_args, **_kwargs: pytest.fail("query called"),
        query_task_dependencies_page=lambda *_args, **_kwargs: pytest.fail("query called"),
        query_task_activity_page=lambda *_args, **_kwargs: pytest.fail("query called"),
    )
    api = build_project_management_tasks_desktop_api(
        task_detail_query=query,
        module_catalog_service=catalog,
    )

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        getattr(api, method)("task-1")


def test_dependency_previews_use_composed_handler(services) -> None:
    project = services["project_service"].create_project("Dependency Preview")
    tasks = services["task_service"]
    predecessor = tasks.create_task(project.id, "Predecessor")
    successor = tasks.create_task(project.id, "Successor")
    api = build_project_management_tasks_desktop_api(
        task_service=tasks,
        task_dependency_diagnostics=services["task_dependency_diagnostics"],
        module_catalog_service=services["module_catalog_service"],
    )
    create = TaskDependencyCreateCommand(
        task_id=successor.id,
        linked_task_id=predecessor.id,
        relationship_direction="PREDECESSOR",
    )
    assert api.preview_create_dependency(create).is_valid
    dependency = tasks.add_dependency(predecessor.id, successor.id, DependencyType.FINISH_TO_START)
    assert api.preview_update_dependency(
        TaskDependencyUpdateCommand(dependency_id=dependency.id)
    ).is_valid
    assert api.preview_delete_dependency(dependency.id).is_valid
    assert tasks.get_dependency(dependency.id) is not None


@pytest.mark.parametrize("method", ("create", "update", "delete"))
def test_dependency_previews_check_module_before_handler(method: str) -> None:
    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    diagnostics = SimpleNamespace(
        get_dependency_diagnostics=lambda *_args, **_kwargs: pytest.fail("query called"),
        preview_dependency_removal=lambda *_args: pytest.fail("query called"),
    )
    api = build_project_management_tasks_desktop_api(
        task_service=SimpleNamespace(get_dependency=lambda *_args: pytest.fail("query called")),
        task_dependency_diagnostics=diagnostics,
        module_catalog_service=catalog,
    )
    calls = {
        "create": lambda: api.preview_create_dependency(
            TaskDependencyCreateCommand("task", "linked", "PREDECESSOR")
        ),
        "update": lambda: api.preview_update_dependency(
            TaskDependencyUpdateCommand("dependency")
        ),
        "delete": lambda: api.preview_delete_dependency("dependency"),
    }
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        calls[method]()


@pytest.mark.parametrize("method", ("get_task_time_summary", "list_task_time_entries"))
def test_task_detail_time_checks_module_before_handler(method: str) -> None:
    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    assignment = SimpleNamespace(
        get_task_time_summary=lambda *_args: pytest.fail("summary called")
    )
    time_entries = SimpleNamespace(
        list_time_entries_for_task_page=lambda *_args, **_kwargs: pytest.fail("query called")
    )
    api = build_project_management_tasks_desktop_api(
        task_assignment_commands=assignment,
        task_time_entries=time_entries,
        module_catalog_service=catalog,
    )

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        getattr(api, method)("task-1")
