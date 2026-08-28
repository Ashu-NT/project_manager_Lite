from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.uow.employee_unit_of_work import EmployeeUnitOfWork
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    LinkedEmployeeResourceRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.department.departments import (
    SqlAlchemyDepartmentRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.employee.employee import (
    SqlAlchemyEmployeeRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
    SqlAlchemySiteRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import (
    SqlAlchemyUnitOfWorkBase,
    SqlAlchemyUnitOfWorkFactoryBase,
)


class SqlAlchemyEmployeeUnitOfWork(SqlAlchemyUnitOfWorkBase, EmployeeUnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        tenant_context_service,
        user_session,
        resource_repo_factory: Callable[[Session], LinkedEmployeeResourceRepository],
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.employees = SqlAlchemyEmployeeRepository(session)
        self.resources = resource_repo_factory(session)
        self.sites = SqlAlchemySiteRepository(session)
        self.departments = SqlAlchemyDepartmentRepository(session)
        for repo in (self.employees, self.resources, self.sites, self.departments):
            if hasattr(repo, "_tenant_context_service"):
                repo._tenant_context_service = tenant_context_service

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyEmployeeUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service,
        user_session,
        resource_repo_factory: Callable[[Session], LinkedEmployeeResourceRepository],
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._resource_repo_factory = resource_repo_factory

    def create(self, *, context: DomainEventContext) -> SqlAlchemyEmployeeUnitOfWork:
        return SqlAlchemyEmployeeUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
            resource_repo_factory=self._resource_repo_factory,
        )


__all__ = ["SqlAlchemyEmployeeUnitOfWork", "SqlAlchemyEmployeeUnitOfWorkFactory"]
