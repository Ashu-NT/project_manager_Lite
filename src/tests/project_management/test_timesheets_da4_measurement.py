from __future__ import annotations

from sqlalchemy import event

from src.core.modules.project_management.contracts.repositories.task import (
    TimesheetAssignmentContext,
)


def test_timesheet_assignment_context_is_one_tenant_scoped_query(
    services,
    session,
) -> None:
    project = services["project_service"].create_project("DA4 Timesheets")
    task = services["task_service"].create_task(project.id, "Review commissioning")
    resource = services["resource_service"].create_resource("Commissioning Lead")
    assignment = services["task_service"].assign_resource(
        task.id,
        resource.id,
        allocation_percent=75.0,
    )

    statements: list[str] = []
    engine = session.get_bind()

    def count_statement(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        statements.append(str(statement))

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        rows = services["task_service"].list_timesheet_assignment_contexts(
            project_id=project.id
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assignment_projection_statements = [
        statement
        for statement in statements
        if "task_assignments" in statement
        and "JOIN tasks" in statement
        and "JOIN resources" in statement
    ]
    assert len(assignment_projection_statements) == 1
    assert len(statements) <= 2  # Includes the bounded runtime-session lease check.
    assert rows == [
        TimesheetAssignmentContext(
            assignment_id=assignment.id,
            project_id=project.id,
            project_name=project.name,
            task_id=task.id,
            task_name=task.name,
            resource_id=resource.id,
            resource_name=resource.name,
        )
    ]
