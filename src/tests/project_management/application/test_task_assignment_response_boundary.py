from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import event

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.responses.assignment import (
    TaskAssignmentResponseDto,
)


def test_assignment_response_enrichment_batches_queries_for_undated_task(services, session):
    project = services["project_create"].create_project(ProjectCreateCommand(name="Assignment responses"))
    task = services["task_lifecycle_commands"].create_task(TaskCreateCommand(project.id, "Undated work"))
    commands = services["task_assignment_commands"]
    engine = session.get_bind()

    def add_assignment(index):
        resource = services["resource_master_commands"].create_resource(
            ResourceCreateCommand(name=f"Worker {index}")
        )
        commands.assign_resource(task.id, resource.id)

    def measure():
        statements = []

        def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        session.expire_all()
        event.listen(engine, "before_cursor_execute", capture)
        try:
            rows = commands.query_assignment_responses(task.id)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        return rows, statements

    add_assignment(0)
    one_row, one_queries = measure()
    for index in range(1, 8):
        add_assignment(index)
    many_rows, many_queries = measure()

    assert len(one_row) == 1
    assert len(many_rows) == 8
    assert len(many_queries) == len(one_queries)
    assert sum("FROM resources " in sql for sql in many_queries) == 1
    assert sum("FROM project_resources " in sql for sql in many_queries) == 1
    assert all(isinstance(row, TaskAssignmentResponseDto) for row in many_rows)
    assert all(isinstance(row.hours_logged, Decimal) for row in many_rows)
    assert all(row.can_manage for row in many_rows)
    assert all(row.capacity is None for row in many_rows)


def test_dated_assignment_response_keeps_the_authoritative_capacity_fact(services):
    project = services["project_create"].create_project(ProjectCreateCommand(name="Capacity response"))
    start = date.today() + timedelta(days=1)
    first = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(project.id, "First", start_date=start, duration_days=3)
    )
    second = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(project.id, "Second", start_date=start, duration_days=3)
    )
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Shared worker"))
    commands = services["task_assignment_commands"]
    assignment = commands.assign_resource(first.id, resource.id, allocation_percent=70)
    commands.assign_resource(second.id, resource.id, allocation_percent=60)

    response = commands.query_assignment_responses(first.id)[0]
    expected = commands.preview_assignment_capacity(
        first.id, resource.id, proposed_allocation_percent=70, exclude_assignment_id=assignment.id
    )

    assert response.capacity is not None
    assert response.capacity == expected
    assert response.capacity.capacity_status == "OVER_CAPACITY"
    assert response.capacity.peak_utilization_percent > 100
