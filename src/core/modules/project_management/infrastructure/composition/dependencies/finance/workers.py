from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.commitments.commands import (
    ProjectCommitmentCommandHandler,
)
from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    ApprovedTimeLaborCostConsumer,
)
from src.core.modules.project_management.application.financials.cost.entries.commands import (
    ApprovedTimeCostEntryCommandHandler,
    ProcurementReceiptCostEntryCommandHandler,
)
from src.core.modules.project_management.application.financials.integration.procurement_consumer import (
    ProcurementFinancialConsumer,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.finance.queries.financial_period_query import (
    FinancialPeriodQueryHandler,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


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
    Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal], ApprovedTimeLaborCostConsumer
    ],
    Callable[
        [FinanceGovernanceUnitOfWork, ServicePrincipal], ProcurementFinancialConsumer
    ],
]:
    def build_approved_time_consumer(
        uow: FinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ApprovedTimeLaborCostConsumer:
        if not isinstance(uow, SqlAlchemyFinanceGovernanceUnitOfWork):
            raise TypeError("Finance worker requires the SQLAlchemy unit of work")
        worker_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
        )
        approved_time_commands = ApprovedTimeCostEntryCommandHandler(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_queries=FinancialPeriodQueryHandler(
                period_repo=uow.financial_periods,
                user_session=platform_services.user_session,
            ),
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            rate_resolver=worker_rate_resolver,
            labor_posting_repo=uow.labor_postings,
            # The inbox worker collects the returned facts into this UoW.
            record_event=None,
        )
        return ApprovedTimeLaborCostConsumer(
            cost_entry_commands=approved_time_commands,
            service_principal=principal,
        )

    def build_procurement_consumer(
        uow: FinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ProcurementFinancialConsumer:
        if not isinstance(uow, SqlAlchemyFinanceGovernanceUnitOfWork):
            raise TypeError("Finance worker requires the SQLAlchemy unit of work")
        commitment_commands = ProjectCommitmentCommandHandler(
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
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=None,
        )
        receipt_commands = ProcurementReceiptCostEntryCommandHandler(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_queries=FinancialPeriodQueryHandler(
                period_repo=uow.financial_periods,
                user_session=platform_services.user_session,
            ),
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=None,
        )
        return ProcurementFinancialConsumer(
            commitment_commands=commitment_commands,
            receipt_commands=receipt_commands,
            task_repo=uow.tasks,
            service_principal=principal,
        )

    return build_approved_time_consumer, build_procurement_consumer
