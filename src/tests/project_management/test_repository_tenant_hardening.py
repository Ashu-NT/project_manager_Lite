from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    ProjectBaseline,
)
from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    BaselineVarianceRecordORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import (
    CalendarEventORM,
    CostItemORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration import (
    SqlAlchemyTaskPresenceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.task import (
    SqlAlchemyDependencyRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


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
    assignment_a = TaskAssignmentORM(
        id="assignment-a",
        task_id=task_a1.id,
        resource_id=resource_a.id,
        allocation_percent=100.0,
        hours_logged=0.0,
    )
    assignment_b = TaskAssignmentORM(
        id="assignment-b",
        task_id=task_b1.id,
        resource_id=resource_b.id,
        allocation_percent=100.0,
        hours_logged=0.0,
    )
    dependency_a = TaskDependencyORM(
        id="dependency-a",
        predecessor_task_id=task_a1.id,
        successor_task_id=task_a2.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
    )
    dependency_b = TaskDependencyORM(
        id="dependency-b",
        predecessor_task_id=task_b1.id,
        successor_task_id=task_b2.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
    )
    comment_a = TaskCommentORM(
        id="comment-a",
        task_id=task_a1.id,
        author_user_id="user-a",
        author_username="alice",
        body="Comment A",
        mentions_json="[]",
        mentioned_user_ids_json="[]",
        attachments_json="[]",
        read_by_json="[]",
        read_by_user_ids_json="[]",
        created_at=now,
    )
    comment_b = TaskCommentORM(
        id="comment-b",
        task_id=task_b1.id,
        author_user_id="user-b",
        author_username="bob",
        body="Comment B",
        mentions_json="[]",
        mentioned_user_ids_json="[]",
        attachments_json="[]",
        read_by_json="[]",
        read_by_user_ids_json="[]",
        created_at=now,
    )
    presence_a = TaskPresenceORM(
        id="presence-a",
        task_id=task_a1.id,
        user_id="user-a",
        username="alice",
        display_name="Alice",
        activity="reviewing",
        started_at=now,
        last_seen_at=now,
    )
    presence_b = TaskPresenceORM(
        id="presence-b",
        task_id=task_b1.id,
        user_id="user-b",
        username="bob",
        display_name="Bob",
        activity="reviewing",
        started_at=now,
        last_seen_at=now,
    )
    cost_a = CostItemORM(
        id="cost-a",
        project_id=project_a.id,
        task_id=task_a1.id,
        description="Cost A",
        cost_type=CostType.OVERHEAD.value,
        planned_amount=100.0,
        committed_amount=0.0,
        actual_amount=0.0,
        version=1,
    )
    cost_b = CostItemORM(
        id="cost-b",
        project_id=project_b.id,
        task_id=task_b1.id,
        description="Cost B",
        cost_type=CostType.OVERHEAD.value,
        planned_amount=200.0,
        committed_amount=0.0,
        actual_amount=0.0,
        version=1,
    )
    event_a = CalendarEventORM(
        id="event-a",
        title="Event A",
        start_date=today,
        end_date=today,
        project_id=project_a.id,
        task_id=task_a1.id,
        all_day=True,
        description="",
    )
    event_b = CalendarEventORM(
        id="event-b",
        title="Event B",
        start_date=today,
        end_date=today,
        project_id=project_b.id,
        task_id=task_b1.id,
        all_day=True,
        description="",
    )
    register_a = RegisterEntryORM(
        id="register-a",
        project_id=project_a.id,
        entry_type=RegisterEntryType.RISK,
        title="Register A",
        description="",
        severity=RegisterEntrySeverity.MEDIUM,
        status=RegisterEntryStatus.OPEN,
        impact_summary="",
        response_plan="",
        created_at=now,
        updated_at=now,
        version=1,
    )
    register_b = RegisterEntryORM(
        id="register-b",
        project_id=project_b.id,
        entry_type=RegisterEntryType.RISK,
        title="Register B",
        description="",
        severity=RegisterEntrySeverity.MEDIUM,
        status=RegisterEntryStatus.OPEN,
        impact_summary="",
        response_plan="",
        created_at=now,
        updated_at=now,
        version=1,
    )
    baseline_a = ProjectBaselineORM(
        id="baseline-a",
        project_id=project_a.id,
        name="Baseline A",
        created_at=now,
        status=BaselineStatus.DRAFT.value,
        version=1,
    )
    baseline_b = ProjectBaselineORM(
        id="baseline-b",
        project_id=project_b.id,
        name="Baseline B",
        created_at=now,
        status=BaselineStatus.DRAFT.value,
        version=1,
    )
    baseline_task_a = BaselineTaskORM(
        id="baseline-task-a",
        baseline_id=baseline_a.id,
        task_id=task_a1.id,
        task_name="Task A1",
        baseline_start=today,
        baseline_finish=today,
        baseline_duration_days=1,
        baseline_planned_cost=100.0,
    )
    baseline_task_b = BaselineTaskORM(
        id="baseline-task-b",
        baseline_id=baseline_b.id,
        task_id=task_b1.id,
        task_name="Task B1",
        baseline_start=today,
        baseline_finish=today,
        baseline_duration_days=1,
        baseline_planned_cost=200.0,
    )
    variance_a = BaselineVarianceRecordORM(
        id="variance-a",
        project_id=project_a.id,
        new_baseline_id=baseline_a.id,
        superseded_baseline_id=baseline_a.id,
        task_id=task_a1.id,
        task_name="Task A1",
        start_variance_days=0,
        finish_variance_days=0,
        cost_variance=0.0,
        created_at=today,
    )
    variance_b = BaselineVarianceRecordORM(
        id="variance-b",
        project_id=project_b.id,
        new_baseline_id=baseline_b.id,
        superseded_baseline_id=baseline_b.id,
        task_id=task_b1.id,
        task_name="Task B1",
        start_variance_days=0,
        finish_variance_days=0,
        cost_variance=0.0,
        created_at=today,
    )

    session.add_all(
        [
            project_a,
            project_b,
            resource_a,
            resource_b,
            task_a1,
            task_a2,
            task_b1,
            task_b2,
        ]
    )
    session.commit()
    session.add_all(
        [
            assignment_a,
            assignment_b,
            dependency_a,
            dependency_b,
            comment_a,
            comment_b,
            presence_a,
            presence_b,
            cost_a,
            cost_b,
            event_a,
            event_b,
            register_a,
            register_b,
            baseline_a,
            baseline_b,
        ]
    )
    session.commit()
    session.add_all(
        [
            baseline_task_a,
            baseline_task_b,
            variance_a,
            variance_b,
        ]
    )
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
        "event_a": event_a.id,
        "event_b": event_b.id,
        "register_a": register_a.id,
        "register_b": register_b.id,
        "baseline_a": baseline_a.id,
        "baseline_b": baseline_b.id,
    }


def test_priority_pm_repositories_hide_other_organization_rows(services):
    seeded = _seed_priority_pm_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    task_repo = services["task_service"]._task_repo
    assignment_repo = services["task_service"]._assignment_repo
    dependency_repo = services["task_service"]._dependency_repo
    comment_repo = services["collaboration_service"]._comment_repo
    presence_repo = services["collaboration_service"]._presence_repo
    cost_repo = services["cost_service"]._cost_repo
    calendar_repo = services["calendar_service"]._calendar_repo
    register_repo = services["register_service"]._register_repo
    baseline_repo = services["baseline_service"]._baselines

    assert task_repo.get(seeded["task_b1"]) is None
    assert [row.id for row in task_repo.list_by_project(seeded["project_b"])] == []

    assert assignment_repo.get(seeded["assignment_b"]) is None
    assert assignment_repo.list_by_task(seeded["task_b1"]) == []
    assert assignment_repo.list_by_resource(seeded["resource_b"]) == []
    assert [row.id for row in assignment_repo.list_by_tasks([seeded["task_a1"], seeded["task_b1"]])] == [
        seeded["assignment_a"]
    ]

    assert dependency_repo.get(seeded["dependency_b"]) is None
    assert dependency_repo.list_by_project(seeded["project_b"]) == []
    assert dependency_repo.list_by_task(seeded["task_b1"]) == []

    assert comment_repo.get(seeded["comment_b"]) is None
    assert comment_repo.list_by_task(seeded["task_b1"]) == []
    assert [row.id for row in comment_repo.list_recent_for_tasks([seeded["task_a1"], seeded["task_b1"]])] == [
        seeded["comment_a"]
    ]

    presence_rows = presence_repo.list_recent_for_tasks(
        [seeded["task_a1"], seeded["task_b1"]],
        since=datetime.now() - timedelta(days=1),
        limit=20,
    )
    assert [row.id for row in presence_rows] == ["presence-a"]

    assert cost_repo.get(seeded["cost_b"]) is None
    assert cost_repo.list_by_project(seeded["project_b"]) == []

    assert calendar_repo.get(seeded["event_b"]) is None
    assert calendar_repo.list_for_project(seeded["project_b"]) == []
    assert [row.id for row in calendar_repo.list_range(date.today(), date.today())] == [seeded["event_a"]]

    assert register_repo.get(seeded["register_b"]) is None
    assert register_repo.list_entries(project_id=seeded["project_b"]) == []
    assert [row.id for row in register_repo.list_entries()] == [seeded["register_a"]]

    assert baseline_repo.get_baseline(seeded["baseline_b"]) is None
    assert baseline_repo.list_for_project(seeded["project_b"]) == []
    assert baseline_repo.list_tasks(seeded["baseline_b"]) == []
    assert baseline_repo.list_variance_records(seeded["baseline_b"]) == []


def test_priority_pm_repositories_scope_mutations_to_active_organization(services):
    seeded = _seed_priority_pm_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    task_repo = services["task_service"]._task_repo
    assignment_repo = services["task_service"]._assignment_repo
    dependency_repo = services["task_service"]._dependency_repo
    cost_repo = services["cost_service"]._cost_repo
    calendar_repo = services["calendar_service"]._calendar_repo
    register_repo = services["register_service"]._register_repo
    baseline_repo = services["baseline_service"]._baselines

    assignment_repo.delete(seeded["assignment_b"])
    assignment_repo.delete_by_task(seeded["task_b1"])
    dependency_repo.delete(seeded["dependency_b"])
    dependency_repo.delete_for_task(seeded["task_b1"])
    cost_repo.delete(seeded["cost_b"])
    cost_repo.delete_by_project(seeded["project_b"])
    calendar_repo.delete(seeded["event_b"])
    calendar_repo.delete_for_task(seeded["task_b1"])
    calendar_repo.delete_for_project(seeded["project_b"])
    register_repo.delete(seeded["register_b"])
    baseline_repo.delete_tasks(seeded["baseline_b"])
    baseline_repo.delete_baseline(seeded["baseline_b"])
    task_repo.delete(seeded["task_b1"])
    services["session"].commit()

    organization_service.set_active_organization(seeded["other_org"].id)

    assert task_repo.get(seeded["task_b1"]) is not None
    assert assignment_repo.get(seeded["assignment_b"]) is not None
    assert dependency_repo.get(seeded["dependency_b"]) is not None
    assert cost_repo.get(seeded["cost_b"]) is not None
    assert calendar_repo.get(seeded["event_b"]) is not None
    assert register_repo.get(seeded["register_b"]) is not None
    assert baseline_repo.get_baseline(seeded["baseline_b"]) is not None
    assert [row.id for row in baseline_repo.list_tasks(seeded["baseline_b"])] == ["baseline-task-b"]


def test_priority_pm_repositories_reject_cross_organization_updates(services):
    seeded = _seed_priority_pm_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    task_repo = services["task_service"]._task_repo
    assignment_repo = services["task_service"]._assignment_repo
    dependency_repo = services["task_service"]._dependency_repo
    comment_repo = services["collaboration_service"]._comment_repo
    cost_repo = services["cost_service"]._cost_repo
    calendar_repo = services["calendar_service"]._calendar_repo
    register_repo = services["register_service"]._register_repo
    baseline_repo = services["baseline_service"]._baselines

    with pytest.raises(NotFoundError):
        task_repo.update(Task(id=seeded["task_b1"], project_id=seeded["project_b"], name="Blocked"))
    with pytest.raises(NotFoundError):
        assignment_repo.update(
            TaskAssignment(
                id=seeded["assignment_b"],
                task_id=seeded["task_b1"],
                resource_id=seeded["resource_b"],
                allocation_percent=50.0,
            )
        )
    with pytest.raises(NotFoundError):
        dependency_repo.update(
            TaskDependency(
                id=seeded["dependency_b"],
                predecessor_task_id=seeded["task_b1"],
                successor_task_id=seeded["task_b2"],
                dependency_type=DependencyType.FINISH_TO_START,
                lag_days=2,
            )
        )
    with pytest.raises(NotFoundError):
        comment_repo.update(
            TaskComment(
                id=seeded["comment_b"],
                task_id=seeded["task_b1"],
                author_user_id="user-b",
                author_username="bob",
                body="Blocked",
                created_at=datetime.now(timezone.utc),
            )
        )
    with pytest.raises(BusinessRuleError):
        cost_repo.update(
            CostItem(
                id=seeded["cost_b"],
                project_id=seeded["project_b"],
                task_id=seeded["task_b1"],
                description="Blocked",
                planned_amount=250.0,
            )
        )
    with pytest.raises(NotFoundError):
        calendar_repo.update(
            CalendarEvent(
                id=seeded["event_b"],
                title="Blocked",
                start_date=date.today(),
                end_date=date.today(),
                project_id=seeded["project_b"],
                task_id=seeded["task_b1"],
            )
        )
    with pytest.raises(BusinessRuleError):
        register_repo.update(
            RegisterEntry(
                id=seeded["register_b"],
                project_id=seeded["project_b"],
                entry_type=RegisterEntryType.RISK,
                title="Blocked",
            )
        )
    with pytest.raises(NotFoundError):
        baseline_repo.update_baseline(
            ProjectBaseline(
                id=seeded["baseline_b"],
                project_id=seeded["project_b"],
                name="Blocked",
                created_at=date.today(),
            )
        )


def test_dependency_and_presence_repositories_require_tenant_context_service(session):
    dependency_repo = SqlAlchemyDependencyRepository(session)
    presence_repo = SqlAlchemyTaskPresenceRepository(session)

    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        dependency_repo.list_by_task("task-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        presence_repo.list_recent_for_tasks(
            ["task-x"],
            since=datetime.now() - timedelta(minutes=5),
            limit=10,
        )
