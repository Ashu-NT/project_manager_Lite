from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.uow.resources.resource_unit_of_work import (
    ResourceUnitOfWork,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.resource import (
    SqlAlchemyResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.skills import (
    SqlAlchemyResourceCertificationRepository,
    SqlAlchemyResourceSkillRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import (
    SqlAlchemyActivityRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context
from src.infra.persistence.db.unit_of_work import (
    SqlAlchemyUnitOfWorkBase,
    SqlAlchemyUnitOfWorkFactoryBase,
)


class SqlAlchemyResourceUnitOfWork(SqlAlchemyUnitOfWorkBase, ResourceUnitOfWork):
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
        self.resources = SqlAlchemyResourceRepository(session)
        self.skills = SqlAlchemyResourceSkillRepository(session)
        self.certifications = SqlAlchemyResourceCertificationRepository(session)
        for repository in (self.resources, self.skills, self.certifications):
            if hasattr(repository, "_tenant_context_service"):
                repository._tenant_context_service = tenant_context_service

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )

        # Activity-feed staging must ride this same fresh transaction -- a separately-scoped
        # ActivityService bound to a different (process-lifetime shared) Session would stage an
        # entry that this UoW's own commit() never persists (a real regression P18A's own
        # convergence would otherwise introduce, since the mutation no longer shares a Session
        # with anything outside this UoW).
        activity_repo = SqlAlchemyActivityRepository(session)
        activity_repo._tenant_context_service = tenant_context_service
        self._activity_service = ActivityService(
            session=session,
            activity_repo=activity_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyResourceUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
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

    def create(self, *, context: DomainEventContext) -> SqlAlchemyResourceUnitOfWork:
        session = self._session_factory()
        configure_session_rls_context(session, user_session=self._user_session)
        return SqlAlchemyResourceUnitOfWork(
            session=session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = ["SqlAlchemyResourceUnitOfWork", "SqlAlchemyResourceUnitOfWorkFactory"]
