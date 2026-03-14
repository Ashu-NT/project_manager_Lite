from __future__ import annotations

from sqlalchemy.orm import Session

from core.platform.common.interfaces import (
    AuditLogRepository,
    PortfolioIntakeRepository,
    PortfolioScoringTemplateRepository,
    PortfolioScenarioRepository,
    ProjectRepository,
    ResourceRepository,
)
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.portfolio.executive import PortfolioExecutiveMixin
from core.modules.project_management.services.portfolio.intake import PortfolioIntakeMixin
from core.modules.project_management.services.portfolio.scenarios import PortfolioScenarioMixin
from core.modules.project_management.services.portfolio.support import PortfolioSupportMixin
from core.modules.project_management.services.portfolio.templates import PortfolioTemplateMixin
from core.modules.project_management.services.reporting import ReportingService


class PortfolioService(
    ProjectManagementModuleGuardMixin,
    PortfolioExecutiveMixin,
    PortfolioIntakeMixin,
    PortfolioScenarioMixin,
    PortfolioSupportMixin,
    PortfolioTemplateMixin,
):
    DEFAULT_TEMPLATE_NAME = "Balanced PMO"
    DEFAULT_TEMPLATE_SUMMARY = "Balanced template for strategic fit, value, urgency, and delivery risk."

    def __init__(
        self,
        *,
        session: Session,
        intake_repo: PortfolioIntakeRepository,
        scoring_template_repo: PortfolioScoringTemplateRepository,
        scenario_repo: PortfolioScenarioRepository,
        audit_repo: AuditLogRepository,
        project_repo: ProjectRepository,
        resource_repo: ResourceRepository,
        reporting_service: ReportingService,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._intake_repo = intake_repo
        self._scoring_template_repo = scoring_template_repo
        self._scenario_repo = scenario_repo
        self._audit_repo = audit_repo
        self._project_repo = project_repo
        self._resource_repo = resource_repo
        self._reporting = reporting_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service


__all__ = ["PortfolioService"]
