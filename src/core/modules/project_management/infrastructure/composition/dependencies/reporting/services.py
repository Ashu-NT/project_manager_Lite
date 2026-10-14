from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.application.reporting import (
    BaselineCompareReportBuilder,
    CostBreakdownReportBuilder,
    EarnedValueReportBuilder,
    LaborReportBuilder,
    ProfitabilityReportBuilder,
    ProjectKpiReportBuilder,
    ReportingAccessPolicy,
    ReportingCostPolicy,
    ScheduleVarianceReportBuilder,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.reporting.bundle import (
    ReportingComposition,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
    SqlAlchemyFinanceBillingReader,
    SqlAlchemyFinanceSnapshotReader,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_reporting_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    scheduling_engine: SchedulingEngine,
    rate_resolver: RateCardResolver,
) -> ReportingComposition:
    module_catalog_service = platform_services.module_catalog_service
    tenant_context_service = platform_services.tenant_context_service
    calendar = platform_services.global_calendar_shim
    finance_snapshot_reader = SqlAlchemyFinanceSnapshotReader(session=session)
    evm_series_reader = SqlAlchemyEvmSeriesReader(session=session)
    access = ReportingAccessPolicy(user_session=platform_services.user_session)
    # One shared cost policy: the single reporting financial authority.
    cost_policy = ReportingCostPolicy(
        rate_resolver=rate_resolver,
        tenant_context_service=tenant_context_service,
        finance_snapshot_reader=finance_snapshot_reader,
        evm_series_reader=evm_series_reader,
    )
    kpi = ProjectKpiReportBuilder(
        access=access,
        cost_policy=cost_policy,
        project_repo=repositories.pm.project_repo,
        task_repo=repositories.pm.task_repo,
        resource_repo=repositories.pm.resource_repo,
        assignment_repo=repositories.pm.assignment_repo,
        scheduling_engine=scheduling_engine,
        calendar=calendar,
        module_catalog_service=module_catalog_service,
    )
    return ReportingComposition(
        kpi=kpi,
        earned_value=EarnedValueReportBuilder(
            access=access,
            cost_policy=cost_policy,
            evm_series_reader=evm_series_reader,
            tenant_context_service=tenant_context_service,
            calendar=calendar,
            module_catalog_service=module_catalog_service,
        ),
        cost_breakdown=CostBreakdownReportBuilder(
            access=access,
            cost_policy=cost_policy,
            module_catalog_service=module_catalog_service,
        ),
        baseline_compare=BaselineCompareReportBuilder(
            access=access,
            baseline_repo=repositories.pm.baseline_repo,
            task_repo=repositories.pm.task_repo,
            module_catalog_service=module_catalog_service,
        ),
        schedule_variance=ScheduleVarianceReportBuilder(
            access=access,
            baseline_repo=repositories.pm.baseline_repo,
            task_repo=repositories.pm.task_repo,
            critical_path=kpi,
            module_catalog_service=module_catalog_service,
        ),
        profitability=ProfitabilityReportBuilder(
            access=access,
            cost_policy=cost_policy,
            project_repo=repositories.pm.project_repo,
            tenant_context_service=tenant_context_service,
            billing_repo=repositories.pm.project_billing_repo,
            financial_profile_repo=repositories.pm.project_financial_profile_repo,
            billing_reader=SqlAlchemyFinanceBillingReader(session=session),
            module_catalog_service=module_catalog_service,
        ),
        labor=LaborReportBuilder(
            access=access,
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
            finance_snapshot_reader=finance_snapshot_reader,
            module_catalog_service=module_catalog_service,
        ),
    )
