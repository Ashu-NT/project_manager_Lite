from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.uow.portfolio.portfolio_unit_of_work import (
    PortfolioUnitOfWorkFactory,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext

from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.portfolio.commands.portfolio_dependencies import PortfolioDependencyCommandMixin
from src.core.modules.project_management.application.portfolio.commands.portfolio_intake import PortfolioIntakeCommandMixin
from src.core.modules.project_management.application.portfolio.commands.portfolio_scenarios import PortfolioScenarioCommandMixin
from src.core.modules.project_management.application.portfolio.commands.portfolio_templates import PortfolioTemplateCommandMixin
from src.core.modules.project_management.application.portfolio.utils.portfolio_support import PortfolioSupportMixin
from src.core.modules.project_management.application.portfolio.queries.portfolio_dependencies import PortfolioDependencyQueryMixin
from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import PortfolioExecutiveQueryMixin
from src.core.modules.project_management.application.portfolio.queries.portfolio_intake import PortfolioIntakeQueryMixin
from src.core.modules.project_management.application.portfolio.queries.portfolio_scenarios import PortfolioScenarioQueryMixin
from src.core.modules.project_management.application.portfolio.queries.portfolio_templates import PortfolioTemplateQueryMixin
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioIntakeRepository,
    PortfolioProjectDependencyRepository,
    PortfolioScoringTemplateRepository,
    PortfolioScenarioRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.reads.portfolio.scenario_reader import (
    PortfolioScenarioReader,
)
from src.core.modules.project_management.contracts.reads.portfolio.heatmap_reader import (
    PortfolioHeatmapReader,
)
from src.core.modules.project_management.contracts.reads.projects.catalog_reader import (
    ProjectCatalogReader,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.common.exceptions import BusinessRuleError


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
        audit_repo: AuditRepository,
        project_repo: ProjectRepository,
        heatmap_reader: PortfolioHeatmapReader,
        scenario_reader: PortfolioScenarioReader,
        calendar: CalendarProtocol,
        project_calendar_adapter: ProjectCalendarAdapter,
        rate_resolver: LaborRateResolver,
        user_session=None,
        module_catalog_service=None,
        tenant_context_service=None,
        project_catalog_reader: ProjectCatalogReader | None = None,
        uow_factory: PortfolioUnitOfWorkFactory | None = None,
    ) -> None:
        self._session = session
        self._intake_repo = intake_repo
        self._dependency_repo = dependency_repo
        self._scoring_template_repo = scoring_template_repo
        self._scenario_repo = scenario_repo
        self._audit_repo = audit_repo
        self._project_repo = project_repo
        self._heatmap_reader = heatmap_reader
        self._scenario_reader = scenario_reader
        self._project_catalog_reader = project_catalog_reader
        self._calendar = calendar
        self._project_calendar_adapter = project_calendar_adapter
        self._rate_resolver = rate_resolver
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        if tenant_context_service is None:
            raise BusinessRuleError(
                "PortfolioService requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        self._tenant_context_service = tenant_context_service
        self._uow_factory: PortfolioUnitOfWorkFactory | None = uow_factory

    def _require_uow_factory(self) -> PortfolioUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Portfolio unit of work is not configured.")
        return self._uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["PortfolioService"]
