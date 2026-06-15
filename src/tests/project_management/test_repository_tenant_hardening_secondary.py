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
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
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
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.tests.project_management._test_repository_tenant_hardening_secondary_helpers import (
    _seed_pm_secondary_scope_rows,
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
