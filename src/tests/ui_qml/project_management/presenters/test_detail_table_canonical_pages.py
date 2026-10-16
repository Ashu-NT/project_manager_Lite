from decimal import Decimal

from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskAssignmentReadItem,
    TaskAssignmentReadPage,
    TaskDependencyReadItem,
    TaskDependencyReadPage,
)
from src.ui_qml.modules.project_management.presenters.common.detail_table_pages import (
    task_assignments_page,
    task_dependencies_page,
)


def test_assignment_page_maps_canonical_fields_and_keeps_authoritative_capabilities():
    item = TaskAssignmentReadItem(
        assignment_id="assignment", resource_id="resource", resource_code="RES-1",
        resource_name="Person", role="Engineer", allocation_percent=Decimal("0"),
        planned_hours=Decimal("0.00"), actual_hours=Decimal("0.00"),
        response_status="pending", project_resource_id="envelope", version=3,
        can_manage=False, can_accept=True, can_decline=True,
    )
    page = TaskAssignmentReadPage(items=(item,), filtered_total=50, page=2,
                                  page_size=25, sort=ReadSort("resourceName"))
    view = task_assignments_page(page, task_id="task")
    row = view["items"][0]
    assert view["total"] == 50
    assert view["page"] == 2
    assert row["id"] == "assignment"
    assert row["state"]["taskId"] == "task"
    assert row["state"]["plannedHours"] == "0.00"
    assert row["state"]["canManage"] is False
    assert row["state"]["canAccept"] is True
    assert row["statusLabel"] == "Pending"


def test_dependency_page_maps_canonical_identity_and_preserves_server_totals():
    item = TaskDependencyReadItem(
        dependency_id="dependency", direction="PREDECESSOR", linked_task_id="linked",
        linked_task_code="TASK-1", linked_task_name="Linked task",
        linked_task_status="IN_PROGRESS", linked_task_start=None, linked_task_end=None,
        dependency_type="FS", lag_days=-2, version=7,
    )
    view = task_dependencies_page(TaskDependencyReadPage(
        items=(item,), filtered_total=10, predecessor_total=8, successor_total=2,
    ))
    row = view["items"][0]
    assert view["total"] == 10
    assert view["predecessorTotal"] == 8
    assert view["successorTotal"] == 2
    assert row["id"] == "dependency"
    assert row["direction"] == "Predecessor"
    assert row["dependencyType"] == "Finish to Start"
    assert row["lagDays"] == "2d lead"
    assert row["state"]["version"] == 7
