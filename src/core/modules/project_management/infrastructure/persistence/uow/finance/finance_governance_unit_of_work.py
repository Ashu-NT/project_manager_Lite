from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import FinanceGovernanceUnitOfWork
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.budgets.budget import SqlAlchemyProjectBudgetRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.commitments.commitment import SqlAlchemyProjectCommitmentRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.configuration.financial_configuration import (
    SqlAlchemyProjectCostCodeRepository,
    SqlAlchemyProjectFinancialProfileRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.cost_entries.cost_entry import SqlAlchemyProjectCostEntryRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.financial_changes.financial_change import SqlAlchemyFinancialChangeRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.forecasts.forecast import SqlAlchemyProjectForecastRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import SqlAlchemyProjectBillingRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.planned_costs.planned_cost import SqlAlchemyProjectPlannedCostVersionRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_cards import SqlAlchemyProjectRateCardRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.register.register import SqlAlchemyRegisterEntryRepository
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyTaskRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.infrastructure.persistence.repositories.approval.approval import SqlAlchemyApprovalRepository
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import SqlAlchemyAuditRepository
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import PostCommitEventPublisher, TransactionalEventDispatcher
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase, SqlAlchemyUnitOfWorkFactoryBase
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context


class SqlAlchemyFinanceGovernanceUnitOfWork(SqlAlchemyUnitOfWorkBase, FinanceGovernanceUnitOfWork):
    def __init__(self, *, session: Session, transactional_dispatcher: TransactionalEventDispatcher,
                 post_commit_bus: PostCommitEventPublisher, context: DomainEventContext,
                 tenant_context_service, user_session) -> None:
        super().__init__(session=session, transactional_dispatcher=transactional_dispatcher,
                         post_commit_bus=post_commit_bus, context=context)
        self.projects = SqlAlchemyProjectRepository(session)
        self.tasks = SqlAlchemyTaskRepository(session)
        self.budgets = SqlAlchemyProjectBudgetRepository(session)
        self.forecasts = SqlAlchemyProjectForecastRepository(session)
        self.changes = SqlAlchemyFinancialChangeRepository(session)
        self.profiles = SqlAlchemyProjectFinancialProfileRepository(session)
        self.cost_codes = SqlAlchemyProjectCostCodeRepository(session)
        self.planned_costs = SqlAlchemyProjectPlannedCostVersionRepository(session)
        self.assignments = SqlAlchemyAssignmentRepository(session)
        self.project_resources = SqlAlchemyProjectResourceRepository(session)
        self.commitments = SqlAlchemyProjectCommitmentRepository(session)
        self.cost_entries = SqlAlchemyProjectCostEntryRepository(session)
        self.register_entries = SqlAlchemyRegisterEntryRepository(session)
        self.approvals = SqlAlchemyApprovalRepository(session)
        self.rate_cards = SqlAlchemyProjectRateCardRepository(session)
        self.billing = SqlAlchemyProjectBillingRepository(session)
        scoped = (
            self.projects, self.tasks, self.budgets, self.forecasts, self.changes,
            self.profiles, self.cost_codes, self.planned_costs, self.assignments,
            self.project_resources, self.commitments, self.cost_entries,
            self.register_entries, self.approvals, self.rate_cards, self.billing,
        )
        for repository in scoped:
            repository._tenant_context_service = tenant_context_service
        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session, audit_repo=audit_repo, user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyFinanceGovernanceUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    def __init__(self, *, session_factory: Callable[[], Session],
                 transactional_dispatcher: TransactionalEventDispatcher,
                 post_commit_bus: PostCommitEventPublisher, tenant_context_service,
                 user_session) -> None:
        super().__init__(session_factory=session_factory,
                         transactional_dispatcher=transactional_dispatcher,
                         post_commit_bus=post_commit_bus)
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyFinanceGovernanceUnitOfWork:
        session = self._session_factory()
        configure_session_rls_context(session, user_session=self._user_session)
        return SqlAlchemyFinanceGovernanceUnitOfWork(
            session=session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = ["SqlAlchemyFinanceGovernanceUnitOfWork", "SqlAlchemyFinanceGovernanceUnitOfWorkFactory"]
