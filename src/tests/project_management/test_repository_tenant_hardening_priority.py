from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.modules.project_management.domain.calendar.assignment import (
    ProjectCalendarAssignment,
    ResourceCalendarAssignment,
)
from src.core.modules.project_management.domain.collaboration import TaskComment
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
    SkillProficiencyLevel,
    TaskSkillRequirement,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    ProjectBaseline,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskPresenceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyDependencyRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def test_priority_pm_repositories_hide_other_organization_rows(services):
    seeded = _seed_priority_pm_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    task_repo = services["task_service"]._task_repo
    assignment_repo = services["task_service"]._assignment_repo
    dependency_repo = services["task_service"]._dependency_repo
    comment_repo = services["collaboration_service"]._comment_repo
    presence_repo = services["collaboration_service"]._presence_repo
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
    register_repo = services["register_service"]._register_repo
    baseline_repo = services["baseline_service"]._baselines

    assignment_repo.delete(seeded["assignment_b"])
    assignment_repo.delete_by_task(seeded["task_b1"])
    dependency_repo.delete(seeded["dependency_b"])
    dependency_repo.delete_for_task(seeded["task_b1"])
    register_repo.delete(seeded["register_b"])
    baseline_repo.delete_tasks(seeded["baseline_b"])
    baseline_repo.delete_baseline(seeded["baseline_b"])
    task_repo.delete(seeded["task_b1"])
    services["session"].commit()

    organization_service.set_active_organization(seeded["other_org"].id)

    assert task_repo.get(seeded["task_b1"]) is not None
    assert assignment_repo.get(seeded["assignment_b"]) is not None
    assert dependency_repo.get(seeded["dependency_b"]) is not None
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
