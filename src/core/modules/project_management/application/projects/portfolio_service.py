from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.projects.commands.portfolio_dependencies import PortfolioDependencyCommandMixin
from src.core.modules.project_management.application.projects.commands.portfolio_intake import PortfolioIntakeCommandMixin
from src.core.modules.project_management.application.projects.commands.portfolio_scenarios import PortfolioScenarioCommandMixin
from src.core.modules.project_management.application.projects.commands.portfolio_templates import PortfolioTemplateCommandMixin
from src.core.modules.project_management.application.projects.portfolio_support import PortfolioSupportMixin
from src.core.modules.project_management.application.projects.queries.portfolio_dependencies import PortfolioDependencyQueryMixin
from src.core.modules.project_management.application.projects.queries.portfolio_executive import PortfolioExecutiveQueryMixin
from src.core.modules.project_management.application.projects.queries.portfolio_intake import PortfolioIntakeQueryMixin
from src.core.modules.project_management.application.projects.queries.portfolio_scenarios import PortfolioScenarioQueryMixin
from src.core.modules.project_management.application.projects.queries.portfolio_templates import PortfolioTemplateQueryMixin
from src.core.modules.project_management.contracts.repositories.portfolio import (
    PortfolioIntakeRepository,
    PortfolioProjectDependencyRepository,
    PortfolioScoringTemplateRepository,
    PortfolioScenarioRepository,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.platform.audit.contracts import AuditLogRepository


class PortfolioService(
    ProjectManagementModuleGuardMixin,
    PortfolioDependencyCommandMixin,
    PortfolioDependencyQueryMixin,
    PortfolioExecutiveQueryMixin,
    PortfolioIntakeCommandMixin,
    PortfolioIntakeQueryMixin,
    PortfolioScenarioCommandMixin,
    PortfolioScenarioQueryMixin,
    PortfolioSupportMixin,
    PortfolioTemplateCommandMixin,
    PortfolioTemplateQueryMixin,
):
    DEFAULT_TEMPLATE_NAME = "Balanced PMO"
    DEFAULT_TEMPLATE_SUMMARY = "Balanced template for strategic fit, value, urgency, and delivery risk."

    def __init__(
        self,
        *,
        session: Session,
        intake_repo: PortfolioIntakeRepository,
        dependency_repo: PortfolioProjectDependencyRepository,
        scoring_template_repo: PortfolioScoringTemplateRepository,
        scenario_repo: PortfolioScenarioRepository,
        audit_repo: AuditLogRepository,
        project_repo: ProjectRepository,
        resource_repo: ResourceRepository,
        reporting_service: ReportingService,
        user_session=None,
        audit_service=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._intake_repo = intake_repo
        self._dependency_repo = dependency_repo
        self._scoring_template_repo = scoring_template_repo
        self._scenario_repo = scenario_repo
        self._audit_repo = audit_repo
        self._project_repo = project_repo
        self._resource_repo = resource_repo
        self._reporting = reporting_service
        self._user_session = user_session
        self._audit_service = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["PortfolioService"]

