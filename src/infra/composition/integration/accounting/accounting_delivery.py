"""External worker composition; no desktop graph, UI session, or vendor import."""

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.persistence.uow.integration.accounting.accounting_delivery import (
    SqlAlchemyAccountingDeliveryTransactions,
)
from src.core.platform.application.integration.accounting.delivery_processor import (
    ExternalAccountingDeliveryProcessor,
)
from src.core.platform.application.security.identity.execution_principal import (
    resolve_execution_principal,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.identity.identity import (
    SqlAlchemyServicePrincipalRepository,
)
from src.infra.composition.accounting_integration import build_accounting_capability
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


def build_external_accounting_processor(
    *,
    engine,
    scope,
    principal_name,
    adapters,
    credentials,
    transactional_dispatcher=None,
    post_commit_bus=None,
    clock=None,
):
    if not principal_name or not principal_name.strip():
        raise ValueError(
            "An explicitly configured Accounting service principal is required."
        )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        validate_postgresql_execution_role(session)
        if engine.dialect.name == "postgresql" and session.scalar(text(
            "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=current_schema() AND c.relname IN "
            "('project_accounting_outbox','project_accounting_handoffs','organization_accounting_connectors') "
            "AND pg_has_role(current_user, c.relowner, 'MEMBER'))"
        )):
            raise ValueError("Accounting worker must use a non-owner database role.")

    def authorize(session, worker_scope):
        principals = SqlAlchemyServicePrincipalRepository(
            session, tenant_context_service=worker_scope
        )
        principal = resolve_execution_principal(
            name=principal_name,
            scope=worker_scope,
            principal_repository=principals,
            user_repository=SqlAlchemyUserRepository(session),
        )
        return principal.user_id

    def capability(session, worker_scope):
        return build_accounting_capability(
            session=session,
            tenant_context_service=worker_scope,
            user_session=worker_scope,
            installed_adapters=frozenset(adapters),
        )

    return ExternalAccountingDeliveryProcessor(
        transactions=SqlAlchemyAccountingDeliveryTransactions(
            session_factory=sessions,
            scope=scope,
            authorize=authorize,
            capability_factory=capability,
            clock=clock or SystemClock(),
            transactional_dispatcher=transactional_dispatcher
            or InProcessTransactionalEventDispatcher(),
            post_commit_bus=post_commit_bus or InProcessPostCommitEventBus(),
        ),
        adapters=adapters,
        credentials=credentials,
    )
