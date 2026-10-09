from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.application.reporting import ReportingService
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
    SqlAlchemyFinanceBillingReader,
    SqlAlchemyFinanceSnapshotReader,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_reporting_service(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    scheduling_engine: SchedulingEngine,
    rate_resolver: RateCardResolver,
) -> ReportingService:
    return ReportingService(
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        assignment_repo=repositories.assignment_repo,
        scheduling_engine=scheduling_engine,
        calendar=platform_services.global_calendar_shim,
        baseline_repo=repositories.baseline_repo,
        project_resource_repo=repositories.project_resource_repo,
        rate_resolver=rate_resolver,
        tenant_context_service=platform_services.tenant_context_service,
        evm_series_reader=SqlAlchemyEvmSeriesReader(session=session),
        finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        financial_profile_repo=repositories.project_financial_profile_repo,
        billing_repo=repositories.project_billing_repo,
        billing_reader=SqlAlchemyFinanceBillingReader(session=session),
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
