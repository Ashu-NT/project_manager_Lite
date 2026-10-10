from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.resources.portfolio.resource_pool_service import (
    PortfolioResourcePoolService,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.portfolio import (
    SqlAlchemyPortfolioHeatmapReader,
    SqlAlchemyPortfolioResourcePoolReader,
    SqlAlchemyPortfolioScenarioReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.projects import (
    SqlAlchemyProjectCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.portfolio.portfolio_unit_of_work import (
    SqlAlchemyPortfolioUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_portfolio_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    project_calendar_adapter: ProjectCalendarAdapter,
    rate_resolver: RateCardResolver,
) -> PortfolioService:
    uow_factory = SqlAlchemyPortfolioUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return PortfolioService(
        session=session,
        intake_repo=repositories.pm.portfolio_intake_repo,
        dependency_repo=repositories.pm.portfolio_project_dependency_repo,
        scoring_template_repo=repositories.pm.portfolio_scoring_template_repo,
        scenario_repo=repositories.pm.portfolio_scenario_repo,
        audit_repo=repositories.platform.audit_entry_repo,
        project_repo=repositories.pm.project_repo,
        heatmap_reader=SqlAlchemyPortfolioHeatmapReader(session=session),
        scenario_reader=SqlAlchemyPortfolioScenarioReader(session=session),
        calendar=platform_services.global_calendar_shim,
        project_calendar_adapter=project_calendar_adapter,
        rate_resolver=rate_resolver,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        project_catalog_reader=SqlAlchemyProjectCatalogReader(session=session),
        uow_factory=uow_factory,
    )


def build_portfolio_resource_pool_service(
    session: Session,
    platform_services: PlatformServiceBundle,
) -> PortfolioResourcePoolService:
    return PortfolioResourcePoolService(
        reader=SqlAlchemyPortfolioResourcePoolReader(session=session),
        calendar=platform_services.global_calendar_shim,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
