from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class ProjectUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for `Project` mutations -- the narrowest explicit UoW for this
    capability. `financial_profiles` is included (not a separate capability UoW) because
    `create_project` creates a `ProjectFinancialProfile` atomically alongside every new Project,
    a same-transaction Project-lifecycle side effect, not a standalone Finance command; Finance's
    own `FinanceGovernanceUnitOfWork` remains the transaction owner for every other
    `ProjectFinancialProfile` mutation (update/transition)."""

    projects: ProjectRepository
    financial_profiles: ProjectFinancialProfileRepository
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class ProjectUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> ProjectUnitOfWork: ...  # type: ignore[override]


__all__ = ["ProjectUnitOfWork", "ProjectUnitOfWorkFactory"]
