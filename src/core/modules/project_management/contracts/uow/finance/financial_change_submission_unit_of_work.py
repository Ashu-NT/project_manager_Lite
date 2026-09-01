from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class FinancialChangeSubmissionUnitOfWork(UnitOfWork, Protocol):
    changes: FinancialChangeRepository
    budgets: ProjectBudgetRepository
    forecasts: ProjectForecastRepository
    approvals: ApprovalRepository
    _enterprise_audit_service: EnterpriseAuditService


class FinancialChangeSubmissionUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> FinancialChangeSubmissionUnitOfWork: ...  # type: ignore[override]


__all__ = [
    "FinancialChangeSubmissionUnitOfWork",
    "FinancialChangeSubmissionUnitOfWorkFactory",
]
