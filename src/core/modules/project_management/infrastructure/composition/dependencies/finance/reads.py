from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials import (
    FinanceService,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
    RateCardResolver,
)
from src.core.modules.project_management.application.reporting import ReportingService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyFinanceBillingReader,
    SqlAlchemyFinanceBudgetReader,
    SqlAlchemyFinanceChangeReader,
    SqlAlchemyFinanceForecastReader,
    SqlAlchemyFinanceIntegrationReader,
    SqlAlchemyFinanceLookupReader,
    SqlAlchemyFinancePerformanceReader,
    SqlAlchemyFinancePlannedCostReader,
    SqlAlchemyFinanceRateReader,
    SqlAlchemyFinanceSetupReader,
    SqlAlchemyFinanceSnapshotReader,
)
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle
from src.infra.composition.integration.accounting.accounting_integration import (
    build_accounting_capability,
)


def build_finance_workspace_query(
    session: Session,
    platform_services: PlatformServiceBundle,
    *,
    accounting_adapter_ids: frozenset[str],
) -> ProjectFinanceWorkspaceQuery:
    return ProjectFinanceWorkspaceQuery(
        accounting_capability=build_accounting_capability(
            session=session,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
            installed_adapters=accounting_adapter_ids,
        ),
        setup_reader=SqlAlchemyFinanceSetupReader(session=session),
        lookup_reader=SqlAlchemyFinanceLookupReader(session=session),
        budget_reader=SqlAlchemyFinanceBudgetReader(session=session),
        planned_cost_reader=SqlAlchemyFinancePlannedCostReader(session=session),
        forecast_reader=SqlAlchemyFinanceForecastReader(session=session),
        rate_reader=SqlAlchemyFinanceRateReader(session=session),
        change_reader=SqlAlchemyFinanceChangeReader(session=session),
        billing_reader=SqlAlchemyFinanceBillingReader(session=session),
        integration_reader=SqlAlchemyFinanceIntegrationReader(session=session),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )


def build_finance_performance_services(
    session: Session,
    platform_services: PlatformServiceBundle,
    *,
    rate_resolver: RateCardResolver,
) -> tuple[SqlAlchemyFinancePerformanceReader, FinanceService]:
    reader = SqlAlchemyFinancePerformanceReader(
        session=session,
        calendar=platform_services.global_calendar_shim,
    )
    service = FinanceService(
        rate_resolver=rate_resolver,
        finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        finance_performance_reader=reader,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    return reader, service


def build_finance_performance_query(
    session: Session,
    platform_services: PlatformServiceBundle,
    *,
    performance_reader: SqlAlchemyFinancePerformanceReader,
    reporting_service: ReportingService,
    baseline_service: BaselineService,
) -> ProjectFinancePerformanceQuery:
    return ProjectFinancePerformanceQuery(
        performance_reader=performance_reader,
        overview_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        earned_value_authority=reporting_service,
        baseline_variance_authority=baseline_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
