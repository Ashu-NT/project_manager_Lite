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
from src.core.modules.project_management.domain.financials.cost import CostItem
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
from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    BaselineVarianceRecordORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment import (
    ProjectCalendarAssignmentORM,
    ResourceCalendarAssignmentORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import (
    CalendarEventORM,
    CostItemORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.portfolio import (
    PortfolioIntakeItemORM,
    PortfolioProjectDependencyORM,
    PortfolioScoringTemplateORM,
    PortfolioScenarioORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.register import RegisterEntryORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
    TaskSkillRequirementORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration import (
    SqlAlchemyTaskPresenceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioProjectDependencyRepository,
    SqlAlchemyPortfolioScoringTemplateRepository,
    SqlAlchemyPortfolioScenarioRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.project import (
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.skills import (
    SqlAlchemyResourceCertificationRepository,
    SqlAlchemyResourceSkillRepository,
    SqlAlchemyTaskSkillRequirementRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.task import (
    SqlAlchemyDependencyRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.infrastructure.persistence.orm.enterprise_calendar import PlatformCalendarORM


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


def _seed_pm_secondary_scope_rows(services):
    seeded = _seed_priority_pm_rows(services)
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = seeded["default_org"]
    other_org = seeded["other_org"]
    other_tenant_id = getattr(other_org, "tenant_id", None) or default_org.tenant_id
    now = datetime.now(timezone.utc)

    project_a_secondary = ProjectORM(
        id="project-a-2",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        name="Project A2",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    project_b_secondary = ProjectORM(
        id="project-b-2",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Project B2",
        status=ProjectStatus.PLANNED,
        version=1,
    )
    calendar_a = PlatformCalendarORM(
        id="pm-calendar-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        code="PM-CAL-A",
        name="PM Calendar A",
        calendar_type="global",
        timezone="UTC",
        is_default=True,
        is_active=True,
        priority=0,
        version=1,
        created_at=now,
        updated_at=now,
    )
    calendar_b = PlatformCalendarORM(
        id="pm-calendar-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        code="PM-CAL-B",
        name="PM Calendar B",
        calendar_type="global",
        timezone="UTC",
        is_default=True,
        is_active=True,
        priority=0,
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add_all([project_a_secondary, project_b_secondary, calendar_a, calendar_b])
    session.commit()

    project_resource_a = ProjectResourceORM(
        id="project-resource-a",
        project_id=seeded["project_a"],
        resource_id=seeded["resource_a"],
        hourly_rate=90.0,
        currency_code="USD",
        planned_hours=24.0,
        is_active=True,
    )
    project_resource_b = ProjectResourceORM(
        id="project-resource-b",
        project_id=seeded["project_b"],
        resource_id=seeded["resource_b"],
        hourly_rate=95.0,
        currency_code="USD",
        planned_hours=32.0,
        is_active=True,
    )
    skill_a = ResourceSkillORM(
        id="skill-a",
        resource_id=seeded["resource_a"],
        skill_code="python",
        skill_name="Python",
        proficiency="advanced",
        version=1,
    )
    skill_b = ResourceSkillORM(
        id="skill-b",
        resource_id=seeded["resource_b"],
        skill_code="plsql",
        skill_name="PL/SQL",
        proficiency="expert",
        version=1,
    )
    cert_a = ResourceCertificationORM(
        id="cert-a",
        resource_id=seeded["resource_a"],
        certification_code="pmp",
        certification_name="PMP",
        version=1,
    )
    cert_b = ResourceCertificationORM(
        id="cert-b",
        resource_id=seeded["resource_b"],
        certification_code="safety",
        certification_name="Safety",
        version=1,
    )
    task_requirement_a = TaskSkillRequirementORM(
        id="task-req-a",
        task_id=seeded["task_a1"],
        skill_code="python",
        required_proficiency="advanced",
        validation_mode="warn",
        version=1,
    )
    task_requirement_b = TaskSkillRequirementORM(
        id="task-req-b",
        task_id=seeded["task_b1"],
        certification_code="safety",
        required_proficiency="intermediate",
        validation_mode="warn",
        version=1,
    )
    project_assignment_a = ProjectCalendarAssignmentORM(
        id="project-calendar-a",
        project_id=seeded["project_a"],
        calendar_id=calendar_a.id,
        is_default=True,
        priority=1,
    )
    project_assignment_b = ProjectCalendarAssignmentORM(
        id="project-calendar-b",
        project_id=seeded["project_b"],
        calendar_id=calendar_b.id,
        is_default=True,
        priority=1,
    )
    resource_assignment_a = ResourceCalendarAssignmentORM(
        id="resource-calendar-a",
        resource_id=seeded["resource_a"],
        calendar_id=calendar_a.id,
        is_default=True,
        priority=1,
    )
    resource_assignment_b = ResourceCalendarAssignmentORM(
        id="resource-calendar-b",
        resource_id=seeded["resource_b"],
        calendar_id=calendar_b.id,
        is_default=True,
        priority=1,
    )
    template_a = PortfolioScoringTemplateORM(
        id="portfolio-template-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        name="Template A",
        summary="Template A",
        strategic_weight=3,
        value_weight=2,
        urgency_weight=2,
        risk_weight=1,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    template_b = PortfolioScoringTemplateORM(
        id="portfolio-template-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Template B",
        summary="Template B",
        strategic_weight=3,
        value_weight=2,
        urgency_weight=2,
        risk_weight=1,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    intake_a = PortfolioIntakeItemORM(
        id="portfolio-intake-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        title="Intake A",
        sponsor_name="Alice",
        summary="Summary A",
        requested_budget=1000.0,
        requested_capacity_percent=10.0,
        strategic_score=4,
        value_score=3,
        urgency_score=2,
        risk_score=1,
        scoring_template_id=template_a.id,
        scoring_template_name=template_a.name,
        strategic_weight=template_a.strategic_weight,
        value_weight=template_a.value_weight,
        urgency_weight=template_a.urgency_weight,
        risk_weight=template_a.risk_weight,
        status="PROPOSED",
        created_at=now,
        updated_at=now,
        version=1,
    )
    intake_b = PortfolioIntakeItemORM(
        id="portfolio-intake-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        title="Intake B",
        sponsor_name="Bob",
        summary="Summary B",
        requested_budget=2000.0,
        requested_capacity_percent=15.0,
        strategic_score=3,
        value_score=4,
        urgency_score=3,
        risk_score=2,
        scoring_template_id=template_b.id,
        scoring_template_name=template_b.name,
        strategic_weight=template_b.strategic_weight,
        value_weight=template_b.value_weight,
        urgency_weight=template_b.urgency_weight,
        risk_weight=template_b.risk_weight,
        status="PROPOSED",
        created_at=now,
        updated_at=now,
        version=1,
    )
    scenario_a = PortfolioScenarioORM(
        id="portfolio-scenario-a",
        tenant_id=default_org.tenant_id,
        organization_id=default_org.id,
        name="Scenario A",
        budget_limit=5000.0,
        capacity_limit_percent=50.0,
        project_ids_json='["project-a","project-a-2"]',
        intake_item_ids_json='["portfolio-intake-a"]',
        notes="Scenario A",
        created_at=now,
        updated_at=now,
    )
    scenario_b = PortfolioScenarioORM(
        id="portfolio-scenario-b",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        name="Scenario B",
        budget_limit=7000.0,
        capacity_limit_percent=60.0,
        project_ids_json='["project-b","project-b-2"]',
        intake_item_ids_json='["portfolio-intake-b"]',
        notes="Scenario B",
        created_at=now,
        updated_at=now,
    )
    dependency_a = PortfolioProjectDependencyORM(
        id="portfolio-dependency-a",
        predecessor_project_id=seeded["project_a"],
        successor_project_id=project_a_secondary.id,
        dependency_type=DependencyType.FINISH_TO_START.value,
        summary="Portfolio dependency A",
        created_at=now,
        updated_at=now,
    )
    dependency_b = PortfolioProjectDependencyORM(
        id="portfolio-dependency-b",
        predecessor_project_id=seeded["project_b"],
        successor_project_id=project_b_secondary.id,
        dependency_type=DependencyType.FINISH_TO_START.value,
        summary="Portfolio dependency B",
        created_at=now,
        updated_at=now,
    )

    session.add_all(
        [
            project_resource_a,
            project_resource_b,
            skill_a,
            skill_b,
            cert_a,
            cert_b,
            task_requirement_a,
            task_requirement_b,
            project_assignment_a,
            project_assignment_b,
            resource_assignment_a,
            resource_assignment_b,
            template_a,
            template_b,
            intake_a,
            intake_b,
            scenario_a,
            scenario_b,
            dependency_a,
            dependency_b,
        ]
    )
    session.commit()
    organization_service.set_active_organization(default_org.id)

    return {
        **seeded,
        "project_a_secondary": project_a_secondary.id,
        "project_b_secondary": project_b_secondary.id,
        "calendar_a": calendar_a.id,
        "calendar_b": calendar_b.id,
        "project_resource_a": project_resource_a.id,
        "project_resource_b": project_resource_b.id,
        "skill_a": skill_a.id,
        "skill_b": skill_b.id,
        "cert_a": cert_a.id,
        "cert_b": cert_b.id,
        "task_requirement_a": task_requirement_a.id,
        "task_requirement_b": task_requirement_b.id,
        "project_assignment_a": project_assignment_a.id,
        "project_assignment_b": project_assignment_b.id,
        "resource_assignment_a": resource_assignment_a.id,
        "resource_assignment_b": resource_assignment_b.id,
        "template_a": template_a.id,
        "template_b": template_b.id,
        "intake_a": intake_a.id,
        "intake_b": intake_b.id,
        "scenario_a": scenario_a.id,
        "scenario_b": scenario_b.id,
        "portfolio_dependency_a": dependency_a.id,
        "portfolio_dependency_b": dependency_b.id,
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


def test_pm_secondary_repositories_hide_other_organization_rows(services):
    seeded = _seed_pm_secondary_scope_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    project_resource_repo = services["project_resource_service"]._project_resource_repo
    resource_service = services["resource_service"]
    skill_repo = resource_service._skill_repo
    cert_repo = resource_service._cert_repo
    requirement_repo = services["assignment_skill_validator"]._requirements
    portfolio_service = services["portfolio_service"]
    intake_repo = portfolio_service._intake_repo
    scenario_repo = portfolio_service._scenario_repo
    dependency_repo = portfolio_service._dependency_repo
    scoring_repo = portfolio_service._scoring_template_repo
    calendar_assignment_service = services["calendar_assignment_service"]
    project_assignment_repo = calendar_assignment_service._project_assignment_repo
    resource_assignment_repo = calendar_assignment_service._resource_assignment_repo

    assert project_resource_repo.get(seeded["project_resource_b"]) is None
    assert project_resource_repo.list_by_project(seeded["project_b"]) == []
    assert project_resource_repo.get_for_project(seeded["project_b"], seeded["resource_b"]) is None

    assert skill_repo.get(seeded["skill_b"]) is None
    assert skill_repo.list_by_resource(seeded["resource_b"]) == []

    assert cert_repo.get(seeded["cert_b"]) is None
    assert cert_repo.list_by_resource(seeded["resource_b"]) == []

    assert requirement_repo.get(seeded["task_requirement_b"]) is None
    assert requirement_repo.list_by_task(seeded["task_b1"]) == []

    assert project_assignment_repo.get(seeded["project_b"]) is None
    assert project_assignment_repo.list_for_project(seeded["project_b"]) == []
    assert project_assignment_repo.list_for_calendar(seeded["calendar_b"]) == []

    assert resource_assignment_repo.get(seeded["resource_b"]) is None
    assert resource_assignment_repo.list_for_resource(seeded["resource_b"]) == []
    assert resource_assignment_repo.list_for_calendar(seeded["calendar_b"]) == []

    assert intake_repo.get(seeded["intake_b"]) is None
    assert all(row.id != seeded["intake_b"] for row in intake_repo.list())

    assert scenario_repo.get(seeded["scenario_b"]) is None
    assert all(row.id != seeded["scenario_b"] for row in scenario_repo.list())

    assert scoring_repo.get(seeded["template_b"]) is None
    assert all(row.id != seeded["template_b"] for row in scoring_repo.list())

    assert dependency_repo.get(seeded["portfolio_dependency_b"]) is None
    assert all(
        row.id != seeded["portfolio_dependency_b"]
        for row in dependency_repo.list()
    )


def test_pm_secondary_repositories_scope_mutations_to_active_organization(services):
    seeded = _seed_pm_secondary_scope_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    project_resource_repo = services["project_resource_service"]._project_resource_repo
    resource_service = services["resource_service"]
    skill_repo = resource_service._skill_repo
    cert_repo = resource_service._cert_repo
    requirement_repo = services["assignment_skill_validator"]._requirements
    portfolio_service = services["portfolio_service"]
    intake_repo = portfolio_service._intake_repo
    scenario_repo = portfolio_service._scenario_repo
    dependency_repo = portfolio_service._dependency_repo
    calendar_assignment_service = services["calendar_assignment_service"]
    project_assignment_repo = calendar_assignment_service._project_assignment_repo
    resource_assignment_repo = calendar_assignment_service._resource_assignment_repo

    project_resource_repo.delete(seeded["project_resource_b"])
    project_resource_repo.delete_by_resource(seeded["resource_b"])
    skill_repo.delete(seeded["skill_b"])
    cert_repo.delete(seeded["cert_b"])
    requirement_repo.delete(seeded["task_requirement_b"])
    project_assignment_repo.delete(seeded["project_assignment_b"])
    resource_assignment_repo.delete(seeded["resource_assignment_b"])
    intake_repo.delete(seeded["intake_b"])
    scenario_repo.delete(seeded["scenario_b"])
    dependency_repo.delete(seeded["portfolio_dependency_b"])
    services["session"].commit()

    organization_service.set_active_organization(seeded["other_org"].id)

    assert project_resource_repo.get(seeded["project_resource_b"]) is not None
    assert skill_repo.get(seeded["skill_b"]) is not None
    assert cert_repo.get(seeded["cert_b"]) is not None
    assert requirement_repo.get(seeded["task_requirement_b"]) is not None
    assert project_assignment_repo.get(seeded["project_b"]) is not None
    assert resource_assignment_repo.get(seeded["resource_b"]) is not None
    assert intake_repo.get(seeded["intake_b"]) is not None
    assert scenario_repo.get(seeded["scenario_b"]) is not None
    assert dependency_repo.get(seeded["portfolio_dependency_b"]) is not None


def test_pm_secondary_repositories_reject_cross_organization_writes(services):
    seeded = _seed_pm_secondary_scope_rows(services)
    organization_service = services["organization_service"]
    organization_service.set_active_organization(seeded["default_org"].id)

    project_resource_repo = services["project_resource_service"]._project_resource_repo
    resource_service = services["resource_service"]
    skill_repo = resource_service._skill_repo
    cert_repo = resource_service._cert_repo
    requirement_repo = services["assignment_skill_validator"]._requirements
    portfolio_service = services["portfolio_service"]
    intake_repo = portfolio_service._intake_repo
    scenario_repo = portfolio_service._scenario_repo
    dependency_repo = portfolio_service._dependency_repo
    scoring_repo = portfolio_service._scoring_template_repo
    calendar_assignment_service = services["calendar_assignment_service"]
    project_assignment_repo = calendar_assignment_service._project_assignment_repo
    resource_assignment_repo = calendar_assignment_service._resource_assignment_repo

    with pytest.raises(NotFoundError):
        project_resource_repo.add(
            ProjectResource(
                id="project-resource-blocked",
                project_id=seeded["project_b"],
                resource_id=seeded["resource_b"],
                hourly_rate=110.0,
                currency_code="USD",
                planned_hours=8.0,
            )
        )
    with pytest.raises(NotFoundError):
        project_resource_repo.update(
            ProjectResource(
                id=seeded["project_resource_b"],
                project_id=seeded["project_b"],
                resource_id=seeded["resource_b"],
                hourly_rate=120.0,
                currency_code="USD",
                planned_hours=16.0,
            )
        )
    with pytest.raises(NotFoundError):
        skill_repo.add(
            ResourceSkill(
                id="skill-blocked",
                resource_id=seeded["resource_b"],
                skill_code="java",
                skill_name="Java",
                proficiency=SkillProficiencyLevel.INTERMEDIATE,
            )
        )
    with pytest.raises(NotFoundError):
        cert_repo.add(
            ResourceCertification(
                id="cert-blocked",
                resource_id=seeded["resource_b"],
                certification_code="blocked",
                certification_name="Blocked",
            )
        )
    with pytest.raises(NotFoundError):
        requirement_repo.add(
            TaskSkillRequirement(
                id="task-req-blocked",
                task_id=seeded["task_b1"],
                skill_code="java",
                required_proficiency=SkillProficiencyLevel.INTERMEDIATE,
            )
        )
    with pytest.raises(NotFoundError):
        project_assignment_repo.save(
            ProjectCalendarAssignment(
                id=seeded["project_assignment_b"],
                project_id=seeded["project_b"],
                calendar_id=seeded["calendar_b"],
                priority=5,
            )
        )
    with pytest.raises(NotFoundError):
        resource_assignment_repo.save(
            ResourceCalendarAssignment(
                id=seeded["resource_assignment_b"],
                resource_id=seeded["resource_b"],
                calendar_id=seeded["calendar_b"],
                priority=5,
            )
        )
    with pytest.raises((NotFoundError, BusinessRuleError)):
        intake_repo.update(
            PortfolioIntakeItem(
                id=seeded["intake_b"],
                organization_id=seeded["other_org"].id,
                title="Blocked",
                sponsor_name="Blocked",
                version=1,
            )
        )
    with pytest.raises((NotFoundError, BusinessRuleError)):
        scenario_repo.update(
            PortfolioScenario(
                id=seeded["scenario_b"],
                organization_id=seeded["other_org"].id,
                name="Blocked",
            )
        )
    with pytest.raises((NotFoundError, BusinessRuleError)):
        scoring_repo.update(
            PortfolioScoringTemplate(
                id=seeded["template_b"],
                organization_id=seeded["other_org"].id,
                name="Blocked",
            )
        )
    with pytest.raises(NotFoundError):
        dependency_repo.add(
            PortfolioProjectDependency(
                id="portfolio-dependency-blocked",
                predecessor_project_id=seeded["project_b"],
                successor_project_id=seeded["project_b_secondary"],
            )
        )


def test_remaining_pm_secondary_repositories_require_tenant_context_service(session):
    project_resource_repo = SqlAlchemyProjectResourceRepository(session)
    intake_repo = SqlAlchemyPortfolioIntakeRepository(session)
    scenario_repo = SqlAlchemyPortfolioScenarioRepository(session)
    dependency_repo = SqlAlchemyPortfolioProjectDependencyRepository(session)
    scoring_repo = SqlAlchemyPortfolioScoringTemplateRepository(session)
    skill_repo = SqlAlchemyResourceSkillRepository(session)
    cert_repo = SqlAlchemyResourceCertificationRepository(session)
    requirement_repo = SqlAlchemyTaskSkillRequirementRepository(session)
    project_assignment_repo = SqlAlchemyProjectCalendarAssignmentRepository(session)
    resource_assignment_repo = SqlAlchemyResourceCalendarAssignmentRepository(session)

    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        project_resource_repo.list_by_project("project-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        intake_repo.get("intake-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        scenario_repo.get("scenario-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        dependency_repo.list()
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        scoring_repo.get("template-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        skill_repo.list_by_resource("resource-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        cert_repo.list_by_resource("resource-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        requirement_repo.list_by_task("task-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        project_assignment_repo.get("project-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        resource_assignment_repo.get("resource-x")
