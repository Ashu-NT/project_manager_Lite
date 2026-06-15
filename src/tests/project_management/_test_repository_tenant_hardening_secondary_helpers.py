from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
)
from src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment import (
    ProjectCalendarAssignmentORM,
    ResourceCalendarAssignmentORM,
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
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
    TaskSkillRequirementORM,
)
from src.core.platform.infrastructure.persistence.orm.enterprise_calendar import PlatformCalendarORM
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


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

    session.add_all([
        project_resource_a, project_resource_b,
        skill_a, skill_b, cert_a, cert_b,
        task_requirement_a, task_requirement_b,
        project_assignment_a, project_assignment_b,
        resource_assignment_a, resource_assignment_b,
        template_a, template_b,
        intake_a, intake_b,
        scenario_a, scenario_b,
        dependency_a, dependency_b,
    ])
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
