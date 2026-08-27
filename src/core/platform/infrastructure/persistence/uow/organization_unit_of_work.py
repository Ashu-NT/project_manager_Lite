"""P4B (Organization Capability Transaction Convergence): `SqlAlchemyOrganizationUnitOfWork` --
Organization's own thin, concrete subclass of the P3 `SqlAlchemyUnitOfWorkBase`, adding exactly
the two named accessors `OrganizationUnitOfWork` declares (`organizations`,
`_enterprise_audit_service`), both bound to this instance's own fresh `Session` -- never the
shared, process-lifetime one every other, not-yet-migrated Platform/PM/Inventory service still
uses. Mirrors `SqlAlchemyPlatformUnitOfWork` (Approval's own capability UoW) exactly, with
`organizations`/`SqlAlchemyOrganizationRepository` standing in for `approvals`/
`SqlAlchemyApprovalRepository`.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.uow.organization_unit_of_work import (
    OrganizationUnitOfWork,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
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


class SqlAlchemyOrganizationUnitOfWork(SqlAlchemyUnitOfWorkBase, OrganizationUnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.organizations = SqlAlchemyOrganizationRepository(session)

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyOrganizationUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over a session *factory* (per ADR-005 Section 6.1 -- never an already-created
    `Session`) plus the ambient collaborators (`tenant_context_service`, `user_session`)
    `SqlAlchemyOrganizationUnitOfWork` needs to build its own two fresh, session-bound accessors
    on every `create()` call. Neither collaborator is itself Session-bound, so both are reused
    as-is across every `create()` call -- only `organizations`/`_enterprise_audit_service` are
    rebuilt fresh, per call, bound to that call's own new `Session`."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyOrganizationUnitOfWork:
        return SqlAlchemyOrganizationUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = ["SqlAlchemyOrganizationUnitOfWork", "SqlAlchemyOrganizationUnitOfWorkFactory"]
