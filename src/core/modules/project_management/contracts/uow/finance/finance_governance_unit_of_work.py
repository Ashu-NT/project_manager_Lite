from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import ProjectBudgetRepository
from src.core.modules.project_management.contracts.repositories.finance.commitments.commitment import ProjectCommitmentRepository
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import ProjectCostEntryRepository
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import FinancialChangeRepository
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import ProjectForecastRepository
from src.core.modules.project_management.contracts.repositories.finance.planned_costs.planned_cost import ProjectPlannedCostVersionRepository
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import ProjectRateCardRepository
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.register.register import RegisterEntryRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class FinanceGovernanceUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for R6C Budget/Forecast/Change/Setup commands."""

    projects: ProjectRepository
    tasks: TaskRepository
    budgets: ProjectBudgetRepository
    forecasts: ProjectForecastRepository
    changes: FinancialChangeRepository
    profiles: ProjectFinancialProfileRepository
    cost_codes: ProjectCostCodeRepository
    planned_costs: ProjectPlannedCostVersionRepository
    assignments: AssignmentRepository
    project_resources: ProjectResourceRepository
    commitments: ProjectCommitmentRepository
    cost_entries: ProjectCostEntryRepository
    register_entries: RegisterEntryRepository
    approvals: ApprovalRepository
    rate_cards: ProjectRateCardRepository
    _enterprise_audit_service: EnterpriseAuditService


class FinanceGovernanceUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> FinanceGovernanceUnitOfWork: ...  # type: ignore[override]


__all__ = ["FinanceGovernanceUnitOfWork", "FinanceGovernanceUnitOfWorkFactory"]
