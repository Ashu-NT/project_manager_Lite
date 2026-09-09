from __future__ import annotations

import pytest

from src.core.modules.project_management.infrastructure.persistence.repositories.scheduling.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioProjectDependencyRepository,
    SqlAlchemyPortfolioScoringTemplateRepository,
    SqlAlchemyPortfolioScenarioRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.configuration.financial_configuration import (
    SqlAlchemyProjectCostCodeRepository,
    SqlAlchemyProjectFinancialProfileRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.skills import (
    SqlAlchemyResourceCertificationRepository,
    SqlAlchemyResourceSkillRepository,
    SqlAlchemyTaskSkillRequirementRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError


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
    financial_profile_repo = SqlAlchemyProjectFinancialProfileRepository(session)
    project_cost_code_repo = SqlAlchemyProjectCostCodeRepository(session)
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
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        financial_profile_repo.get_by_project("project-x")
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        project_cost_code_repo.list()
