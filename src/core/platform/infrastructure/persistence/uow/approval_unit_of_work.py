"""P4 Step 2 (ADR-005 Section 24, Round 7/8): `SqlAlchemyPlatformUnitOfWork` -- Platform's own
thin, concrete subclass of the P3 `SqlAlchemyUnitOfWorkBase`, adding exactly the two named
accessors `PlatformUnitOfWork` declares (`approvals`, `enterprise_audit_service`), both bound to
this instance's own fresh `Session` -- never the shared, process-lifetime one `RepositoryBundle`
still uses for every other, not-yet-migrated Platform/PM/Inventory service.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.persistence.unit_of_work import PlatformUnitOfWork
from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
    SqlAlchemyApprovalRepository,
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


class SqlAlchemyPlatformUnitOfWork(SqlAlchemyUnitOfWorkBase, PlatformUnitOfWork):
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
        approvals = SqlAlchemyApprovalRepository(session)
        approvals._tenant_context_service = tenant_context_service
        self.approvals = approvals

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyPlatformUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over `SessionLocal` (a session *factory*, per ADR-005 Section 6.1 -- never an
    already-created `Session`) plus the ambient collaborators (`tenant_context_service`,
    `user_session`) `SqlAlchemyPlatformUnitOfWork` needs to build its own two fresh, session-bound
    accessors on every `create()` call. Neither collaborator is itself Session-bound, so both are
    reused as-is across every `create()` call (ADR-005 Section 24, Round 7's "ambient
    collaborators ... may be reused as-is" rule) -- only `approvals`/`enterprise_audit_service`
    are rebuilt fresh, per call, bound to that call's own new `Session`."""

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

    def create(self, *, context: DomainEventContext) -> SqlAlchemyPlatformUnitOfWork:
        return SqlAlchemyPlatformUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = ["SqlAlchemyPlatformUnitOfWork", "SqlAlchemyPlatformUnitOfWorkFactory"]
