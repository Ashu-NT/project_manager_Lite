from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from time import perf_counter

from sqlalchemy import event

from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.platform.infrastructure.persistence.orm.history.activity.activity import (
    ActivityEntryORM,
)


def _measure(session, operation):
    statement_count = 0

    def count_statement(*_args, **_kwargs) -> None:
        nonlocal statement_count
        statement_count += 1

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        started = perf_counter()
        result = operation()
        elapsed_ms = (perf_counter() - started) * 1_000
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
    return result, statement_count, elapsed_ms


def test_r5e_bounded_pages_at_long_lived_resource_scale(services) -> None:
    session = services["project_service"]._session
    user_session = services["user_session"]
    tenant_id = user_session.stored_active_tenant_id()
    organization_id = user_session.stored_active_organization_id()
    resource = services["resource_service"].create_resource("R5E Scale Resource")

    project_count = 1_000
    assignment_count = 10_000
    session.bulk_insert_mappings(
        ProjectORM,
        [
            {
                "id": f"r5e-perf-project-{index:04d}",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "project_code": f"R5E-PERF-{index:04d}",
                "name": f"Scale Project {index:04d}",
                "description": "",
                "status": ProjectStatus.ACTIVE,
                "version": 1,
            }
            for index in range(project_count)
        ],
    )
    session.bulk_insert_mappings(
        ProjectResourceORM,
        [
            {
                "id": f"r5e-perf-project-resource-{index:04d}",
                "project_id": f"r5e-perf-project-{index:04d}",
                "resource_id": resource.id,
                "planned_hours": Decimal("100"),
                "is_active": True,
                "version": 1,
            }
            for index in range(project_count)
        ],
    )
    session.bulk_insert_mappings(
        TaskORM,
        [
            {
                "id": f"r5e-perf-task-{index:05d}",
                "project_id": f"r5e-perf-project-{index % project_count:04d}",
                "task_code": f"R5E-TASK-{index:05d}",
                "wbs_code": str(index // project_count + 1),
                "sort_order": index // project_count,
                "name": f"Scale Task {index:05d}",
                "description": "",
                "start_date": date(2026, 8, 1),
                "end_date": date(2026, 8, 5),
                "duration_days": 5,
                "status": TaskStatus.TODO,
                "priority": 0,
                "percent_complete": 0,
                "is_milestone": False,
                "version": 1,
            }
            for index in range(assignment_count)
        ],
    )
    session.bulk_insert_mappings(
        TaskAssignmentORM,
        [
            {
                "id": f"r5e-perf-assignment-{index:05d}",
                "task_id": f"r5e-perf-task-{index:05d}",
                "resource_id": resource.id,
                "allocation_percent": 50,
                "hours_logged": Decimal("0"),
                "allocated_planned_hours": Decimal("8"),
                "version": 1,
                "project_resource_id": (
                    f"r5e-perf-project-resource-{index % project_count:04d}"
                ),
                "response_status": "pending",
            }
            for index in range(assignment_count)
        ],
    )
    occurred_at = datetime(2026, 8, 1)
    session.bulk_insert_mappings(
        ActivityEntryORM,
        [
            {
                "id": f"r5e-perf-activity-{index:05d}",
                "action": "assignment.update",
                "entity_type": "task_assignment",
                "entity_id": f"r5e-perf-assignment-{index:05d}",
                "module": "project_management",
                "workspace_id": f"r5e-perf-project-{index % project_count:04d}",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "timestamp": occurred_at + timedelta(seconds=index),
                "type": "info",
                "human_message": "Assignment updated",
                "details_json": "{}",
                "context_json": "{}",
                "parent_entity_id": f"r5e-perf-task-{index:05d}",
                "related_entity_type": "resource",
                "related_entity_id": resource.id,
                "visibility": "workspace",
            }
            for index in range(assignment_count)
        ],
    )
    session.commit()

    resource_service = services["resource_service"]
    projects, project_statements, project_ms = _measure(
        session,
        lambda: resource_service.query_resource_projects_page(
            resource.id, page=20, page_size=25
        ),
    )
    assignments, assignment_statements, assignment_ms = _measure(
        session,
        lambda: resource_service.query_resource_assignments_page(
            resource.id, lifecycle="all", page=200, page_size=25
        ),
    )
    activity, activity_statements, activity_ms = _measure(
        session,
        lambda: resource_service.query_resource_activity_page(
            resource.id, page=200, page_size=25
        ),
    )

    print(
        "R5E scale "
        f"projects={project_count} ms={project_ms:.2f} statements={project_statements}; "
        f"assignments={assignment_count} ms={assignment_ms:.2f} statements={assignment_statements}; "
        f"activity={assignment_count} ms={activity_ms:.2f} statements={activity_statements}"
    )
    assert projects.filtered_total == project_count and len(projects.items) == 25
    assert assignments.filtered_total == assignment_count and len(assignments.items) == 25
    assert activity.filtered_total == assignment_count + 1 and len(activity.items) == 25
    assert max(project_statements, assignment_statements, activity_statements) <= 3
    assert max(project_ms, assignment_ms, activity_ms) <= 2_000
