from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskCommentRepository,
    SqlAlchemyTaskPresenceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.budgets.budget import (
    SqlAlchemyProjectBudgetRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.commitments.commitment import (
    SqlAlchemyProjectCommitmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.configuration.financial_configuration import (
    SqlAlchemyProjectCostCodeRepository,
    SqlAlchemyProjectFinancialProfileRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.cost_entries.cost_entry import (
    SqlAlchemyProjectCostEntryRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.cost_entries.labor_posting import (
    SqlAlchemyApprovedTimeLaborPostingRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.finance_inbox import (
    SqlAlchemyProjectFinanceInboxRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.financial_changes.financial_change import (
    SqlAlchemyFinancialChangeRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.forecasts.forecast import (
    SqlAlchemyProjectForecastRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
    SqlAlchemyProjectBillingRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.planned_costs.planned_cost import (
    SqlAlchemyProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_cards import (
    SqlAlchemyProjectRateCardRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioProjectDependencyRepository,
    SqlAlchemyPortfolioScenarioRepository,
    SqlAlchemyPortfolioScoringTemplateRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.register.register import (
    SqlAlchemyRegisterEntryRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.resource import (
    SqlAlchemyResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.skills import (
    SqlAlchemyResourceCertificationRepository,
    SqlAlchemyResourceSkillRepository,
    SqlAlchemyTaskSkillRequirementRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.scheduling.baseline import (
    SqlAlchemyBaselineRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.scheduling.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)


@dataclass(frozen=True)
class ProjectManagementRepositories:
    project_repo: SqlAlchemyProjectRepository
    task_repo: SqlAlchemyTaskRepository
    resource_repo: SqlAlchemyResourceRepository
    assignment_repo: SqlAlchemyAssignmentRepository
    dependency_repo: SqlAlchemyDependencyRepository
    project_cost_entry_repo: SqlAlchemyProjectCostEntryRepository
    project_commitment_repo: SqlAlchemyProjectCommitmentRepository
    project_financial_profile_repo: SqlAlchemyProjectFinancialProfileRepository
    project_cost_code_repo: SqlAlchemyProjectCostCodeRepository
    project_rate_card_repo: SqlAlchemyProjectRateCardRepository
    project_budget_repo: SqlAlchemyProjectBudgetRepository
    project_forecast_repo: SqlAlchemyProjectForecastRepository
    financial_change_repo: SqlAlchemyFinancialChangeRepository
    planned_cost_repo: SqlAlchemyProjectPlannedCostVersionRepository
    project_calendar_assignment_repo: SqlAlchemyProjectCalendarAssignmentRepository
    resource_calendar_assignment_repo: SqlAlchemyResourceCalendarAssignmentRepository
    baseline_repo: SqlAlchemyBaselineRepository
    project_resource_repo: SqlAlchemyProjectResourceRepository
    register_repo: SqlAlchemyRegisterEntryRepository
    task_comment_repo: SqlAlchemyTaskCommentRepository
    task_presence_repo: SqlAlchemyTaskPresenceRepository
    portfolio_intake_repo: SqlAlchemyPortfolioIntakeRepository
    portfolio_project_dependency_repo: SqlAlchemyPortfolioProjectDependencyRepository
    portfolio_scoring_template_repo: SqlAlchemyPortfolioScoringTemplateRepository
    portfolio_scenario_repo: SqlAlchemyPortfolioScenarioRepository
    resource_skill_repo: SqlAlchemyResourceSkillRepository
    resource_cert_repo: SqlAlchemyResourceCertificationRepository
    task_skill_req_repo: SqlAlchemyTaskSkillRequirementRepository
    project_finance_inbox_repo: SqlAlchemyProjectFinanceInboxRepository
    approved_time_labor_posting_repo: SqlAlchemyApprovedTimeLaborPostingRepository
    project_billing_repo: SqlAlchemyProjectBillingRepository


def build_project_management_repositories(session: Session) -> ProjectManagementRepositories:
    return ProjectManagementRepositories(
        project_repo=SqlAlchemyProjectRepository(session),
        task_repo=SqlAlchemyTaskRepository(session),
        resource_repo=SqlAlchemyResourceRepository(session),
        assignment_repo=SqlAlchemyAssignmentRepository(session),
        dependency_repo=SqlAlchemyDependencyRepository(session),
        project_cost_entry_repo=SqlAlchemyProjectCostEntryRepository(session),
        project_commitment_repo=SqlAlchemyProjectCommitmentRepository(session),
        project_financial_profile_repo=SqlAlchemyProjectFinancialProfileRepository(session),
        project_cost_code_repo=SqlAlchemyProjectCostCodeRepository(session),
        project_rate_card_repo=SqlAlchemyProjectRateCardRepository(session),
        project_budget_repo=SqlAlchemyProjectBudgetRepository(session),
        project_forecast_repo=SqlAlchemyProjectForecastRepository(session),
        financial_change_repo=SqlAlchemyFinancialChangeRepository(session),
        planned_cost_repo=SqlAlchemyProjectPlannedCostVersionRepository(session),
        project_calendar_assignment_repo=SqlAlchemyProjectCalendarAssignmentRepository(session),
        resource_calendar_assignment_repo=SqlAlchemyResourceCalendarAssignmentRepository(session),
        baseline_repo=SqlAlchemyBaselineRepository(session),
        project_resource_repo=SqlAlchemyProjectResourceRepository(session),
        register_repo=SqlAlchemyRegisterEntryRepository(session),
        task_comment_repo=SqlAlchemyTaskCommentRepository(session),
        task_presence_repo=SqlAlchemyTaskPresenceRepository(session),
        portfolio_intake_repo=SqlAlchemyPortfolioIntakeRepository(session),
        portfolio_project_dependency_repo=SqlAlchemyPortfolioProjectDependencyRepository(session),
        portfolio_scoring_template_repo=SqlAlchemyPortfolioScoringTemplateRepository(session),
        portfolio_scenario_repo=SqlAlchemyPortfolioScenarioRepository(session),
        resource_skill_repo=SqlAlchemyResourceSkillRepository(session),
        resource_cert_repo=SqlAlchemyResourceCertificationRepository(session),
        task_skill_req_repo=SqlAlchemyTaskSkillRequirementRepository(session),
        project_finance_inbox_repo=SqlAlchemyProjectFinanceInboxRepository(session),
        approved_time_labor_posting_repo=SqlAlchemyApprovedTimeLaborPostingRepository(session),
        project_billing_repo=SqlAlchemyProjectBillingRepository(session),
    )
