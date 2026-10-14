from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioDependencyCommandHandler,
    PortfolioIntakeCommandHandler,
    PortfolioScenarioCommandHandler,
    PortfolioTemplateCommandHandler,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioDependencyQueryHandler,
    PortfolioExecutiveQueryHandler,
    PortfolioIntakeQueryHandler,
    PortfolioScenarioQueryHandler,
    PortfolioTemplateQueryHandler,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_heatmap import (
    PortfolioHeatmapCalculator,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
)
from src.core.modules.project_management.application.resources.portfolio.queries.resource_pool import (
    PortfolioResourcePoolQueryHandler,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.portfolio.bundle import (
    PortfolioComposition,
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


def build_portfolio_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    project_calendar_adapter: ProjectCalendarAdapter,
) -> PortfolioComposition:
    uow_factory = SqlAlchemyPortfolioUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    pm = repositories.pm
    tenant_context_service = platform_services.tenant_context_service
    user_session = platform_services.user_session
    module_catalog_service = platform_services.module_catalog_service
    guard: dict[str, Any] = {"user_session": user_session, "module_catalog_service": module_catalog_service}
    policy = PortfolioPolicy(
        tenant_context_service=tenant_context_service,
        project_repo=pm.project_repo,
        intake_repo=pm.portfolio_intake_repo,
        scoring_template_repo=pm.portfolio_scoring_template_repo,
        uow_factory=uow_factory,
        user_session=user_session,
    )
    heatmap_reader = SqlAlchemyPortfolioHeatmapReader(session=session)
    heatmap_calculator = PortfolioHeatmapCalculator(
        calendar=platform_services.global_calendar_shim,
        project_calendar_adapter=project_calendar_adapter,
    )
    executive_query = PortfolioExecutiveQueryHandler(
        heatmap_reader=heatmap_reader,
        heatmap_calculator=heatmap_calculator,
        audit_repo=repositories.platform.audit_entry_repo,
        policy=policy,
        tenant_context_service=tenant_context_service,
        project_catalog_reader=SqlAlchemyProjectCatalogReader(session=session),
        **guard,
    )
    return PortfolioComposition(
        intake_query=PortfolioIntakeQueryHandler(
            intake_repo=pm.portfolio_intake_repo,
            tenant_context_service=tenant_context_service,
            **guard,
        ),
        intake_commands=PortfolioIntakeCommandHandler(
            intake_repo=pm.portfolio_intake_repo,
            policy=policy,
            uow_factory=uow_factory,
            **guard,
        ),
        template_query=PortfolioTemplateQueryHandler(policy=policy, **guard),
        template_commands=PortfolioTemplateCommandHandler(
            scoring_template_repo=pm.portfolio_scoring_template_repo,
            policy=policy,
            uow_factory=uow_factory,
            **guard,
        ),
        scenario_query=PortfolioScenarioQueryHandler(
            scenario_repo=pm.portfolio_scenario_repo,
            scenario_reader=SqlAlchemyPortfolioScenarioReader(session=session),
            calendar=platform_services.global_calendar_shim,
            policy=policy,
            tenant_context_service=tenant_context_service,
            **guard,
        ),
        scenario_commands=PortfolioScenarioCommandHandler(
            scenario_repo=pm.portfolio_scenario_repo,
            policy=policy,
            uow_factory=uow_factory,
            **guard,
        ),
        dependency_query=PortfolioDependencyQueryHandler(
            dependency_repo=pm.portfolio_project_dependency_repo,
            heatmap_reader=heatmap_reader,
            heatmap_calculator=heatmap_calculator,
            executive_query=executive_query,
            policy=policy,
            tenant_context_service=tenant_context_service,
            **guard,
        ),
        dependency_commands=PortfolioDependencyCommandHandler(
            dependency_repo=pm.portfolio_project_dependency_repo,
            policy=policy,
            uow_factory=uow_factory,
            **guard,
        ),
        executive_query=executive_query,
    )


def build_portfolio_resource_pool_query(
    session: Session,
    platform_services: PlatformServiceBundle,
) -> PortfolioResourcePoolQueryHandler:
    return PortfolioResourcePoolQueryHandler(
        reader=SqlAlchemyPortfolioResourcePoolReader(session=session),
        calendar=platform_services.global_calendar_shim,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
