from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskORM,
)
from src.tests.project_management._test_repository_tenant_hardening_row_builders import (
    _build_priority_detail_rows,
)


def _build_priority_core_rows(default_org, other_org, other_tenant_id):
    """Build the core ORM rows (projects, resources, tasks) for priority seed."""
    today = date.today()
    now = datetime.now(timezone.utc)

    project_a = ProjectORM(
        id="project-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        name="Project A",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    project_b = ProjectORM(
        id="project-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Project B",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    resource_a = ResourceORM(
        id="resource-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        name="Resource A",
        role="Planner",
        hourly_rate=90.0,
        is_active=True,
        capacity_percent=100.0,
        cost_type=CostType.LABOR,
        worker_type=WorkerType.EXTERNAL,
        version=1,
    )
    resource_b = ResourceORM(
        id="resource-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Resource B",
        role="Planner",
        hourly_rate=95.0,
        is_active=True,
        capacity_percent=100.0,
        cost_type=CostType.LABOR,
        worker_type=WorkerType.EXTERNAL,
        version=1,
    )
    task_a1 = TaskORM(
        id="task-a-1",
        project_id=project_a.id,
        name="Task A1",
        status=TaskStatus.TODO,
        version=1,
    )
    task_a2 = TaskORM(
        id="task-a-2",
        project_id=project_a.id,
        name="Task A2",
        status=TaskStatus.TODO,
        version=1,
    )
    task_b1 = TaskORM(
        id="task-b-1",
        project_id=project_b.id,
        name="Task B1",
        status=TaskStatus.TODO,
        version=1,
    )
    task_b2 = TaskORM(
        id="task-b-2",
        project_id=project_b.id,
        name="Task B2",
        status=TaskStatus.TODO,
        version=1,
    )
    return today, now, project_a, project_b, resource_a, resource_b, task_a1, task_a2, task_b1, task_b2


def _seed_priority_pm_rows(services):
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    assert default_org is not None
    assert other_org is not None
    assert getattr(default_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or default_org.tenant_id

    today, now, project_a, project_b, resource_a, resource_b, task_a1, task_a2, task_b1, task_b2 = (
        _build_priority_core_rows(default_org, other_org, other_tenant_id)
    )
    (
        assignment_a, assignment_b, dependency_a, dependency_b,
        comment_a, comment_b, presence_a, presence_b,
        cost_a, cost_b,
        register_a, register_b, baseline_a, baseline_b,
        baseline_task_a, baseline_task_b, variance_a, variance_b,
    ) = _build_priority_detail_rows(now, today, project_a, project_b, resource_a, resource_b, task_a1, task_b1, task_a2, task_b2)

    session.add_all([project_a, project_b, resource_a, resource_b, task_a1, task_a2, task_b1, task_b2])
    session.commit()
    session.add_all([
        assignment_a, assignment_b, dependency_a, dependency_b,
        comment_a, comment_b, presence_a, presence_b,
        cost_a, cost_b,
        register_a, register_b, baseline_a, baseline_b,
    ])
    session.commit()
    session.add_all([baseline_task_a, baseline_task_b, variance_a, variance_b])
    session.commit()
    organization_service.set_active_organization(default_org.id)

    return {
        "default_org": default_org,
        "other_org": other_org,
        "project_a": project_a.id,
        "project_b": project_b.id,
        "resource_a": resource_a.id,
        "resource_b": resource_b.id,
        "task_a1": task_a1.id,
        "task_a2": task_a2.id,
        "task_b1": task_b1.id,
        "task_b2": task_b2.id,
        "assignment_a": assignment_a.id,
        "assignment_b": assignment_b.id,
        "dependency_a": dependency_a.id,
        "dependency_b": dependency_b.id,
        "comment_a": comment_a.id,
        "comment_b": comment_b.id,
        "cost_a": cost_a.id,
        "cost_b": cost_b.id,
        "register_a": register_a.id,
        "register_b": register_b.id,
        "baseline_a": baseline_a.id,
        "baseline_b": baseline_b.id,
    }
