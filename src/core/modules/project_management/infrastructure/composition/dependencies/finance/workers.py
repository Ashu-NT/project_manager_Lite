from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    ApprovedTimeLaborCostConsumer,
    ProcurementFinancialConsumer,
    ProjectCommitmentService,
    ProjectCostEntryService,
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle


def build_finance_worker_uow_factory(
    platform_services: PlatformServiceBundle,
) -> SqlAlchemyFinanceGovernanceUnitOfWorkFactory:
    session_factory = sessionmaker(bind=platform_services.session.bind, future=True)
    return SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )


def build_finance_worker_consumers(
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
) -> tuple[
    Callable[[SqlAlchemyFinanceGovernanceUnitOfWork, ServicePrincipal], ApprovedTimeLaborCostConsumer],
    Callable[[SqlAlchemyFinanceGovernanceUnitOfWork, ServicePrincipal], ProcurementFinancialConsumer],
]:
    def build_cost_service(uow: SqlAlchemyFinanceGovernanceUnitOfWork) -> ProjectCostEntryService:
        worker_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
        )
        return ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session,
                period_repo=uow.financial_periods,
                tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            rate_resolver=worker_rate_resolver,
            labor_posting_repo=uow.labor_postings,
        )

    def build_approved_time_consumer(
        uow: SqlAlchemyFinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ApprovedTimeLaborCostConsumer:
        return ApprovedTimeLaborCostConsumer(
            build_cost_service(uow),
            service_principal=principal,
        )

    def build_procurement_consumer(
        uow: SqlAlchemyFinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ProcurementFinancialConsumer:
        worker_commitment_service = ProjectCommitmentService(
            session=uow._session,
            commitment_repo=uow.commitments,
            cost_entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            party_repo=uow.parties,
            site_repo=uow.sites,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
        )
        return ProcurementFinancialConsumer(
            commitment_service=worker_commitment_service,
            cost_entry_service=build_cost_service(uow),
            task_repo=uow.tasks,
            service_principal=principal,
        )

    return build_approved_time_consumer, build_procurement_consumer
