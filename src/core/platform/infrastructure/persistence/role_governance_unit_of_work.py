from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.contract.persistence.role_governance_unit_of_work import (
    RoleGovernanceUnitOfWork,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleBindingRepository,
    SqlAlchemyRoleDelegationPolicyRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
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


class SqlAlchemyRoleGovernanceUnitOfWork(SqlAlchemyUnitOfWorkBase, RoleGovernanceUnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.role_bindings = SqlAlchemyRoleBindingRepository(session)
        self.roles = SqlAlchemyRoleRepository(session)
        self.role_delegation_policies = SqlAlchemyRoleDelegationPolicyRepository(session)
        self.role_permissions = SqlAlchemyRolePermissionRepository(session)
        self.permissions = SqlAlchemyPermissionRepository(session)
        self.users = SqlAlchemyUserRepository(session)
        self.tenants = SqlAlchemyTenantRepository(session)
        self.memberships = SqlAlchemyUserTenantMembershipRepository(session)
        self.audit = SqlAlchemyAuditRepository(session)


class SqlAlchemyRoleGovernanceUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over a session *factory* (per ADR-005 Section 6.1), mirroring every sibling
    Platform UoW factory -- every `create()` call opens a genuinely fresh Session."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )

    def create(self, *, context: DomainEventContext) -> SqlAlchemyRoleGovernanceUnitOfWork:
        return SqlAlchemyRoleGovernanceUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
        )


__all__ = [
    "SqlAlchemyRoleGovernanceUnitOfWork",
    "SqlAlchemyRoleGovernanceUnitOfWorkFactory",
]
