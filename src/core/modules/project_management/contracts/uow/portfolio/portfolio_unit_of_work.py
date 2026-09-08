from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioIntakeRepository,
    PortfolioProjectDependencyRepository,
    PortfolioScenarioRepository,
    PortfolioScoringTemplateRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PortfolioUnitOfWork(UnitOfWork, Protocol):
    
    intake: PortfolioIntakeRepository
    scenarios: PortfolioScenarioRepository
    scoring_templates: PortfolioScoringTemplateRepository
    dependencies: PortfolioProjectDependencyRepository
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class PortfolioUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PortfolioUnitOfWork: ...  # type: ignore[override]


__all__ = ["PortfolioUnitOfWork", "PortfolioUnitOfWorkFactory"]
