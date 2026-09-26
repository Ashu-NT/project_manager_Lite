"""Trusted external endpoint composition; no QML or interactive authority."""

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.integration.accounting.accounting_outcomes import (
    SqlAlchemyAccountingOutcomeConsumer,
)
from src.core.platform.application.integration.accounting.outcome_ingress import (
    AccountingOutcomeIngress,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


def build_external_accounting_ingress(
    *,
    engine,
    authenticator,
    clock=None,
    transactional_dispatcher=None,
    post_commit_bus=None,
):
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        validate_postgresql_execution_role(session)
        if engine.dialect.name == "postgresql" and session.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname=current_schema() AND c.relname IN "
                "('project_finance_inbox_receipts','project_billing_external_events',"
                "'project_billing_preparations','project_accounting_handoffs','organization_accounting_connectors') "
                "AND pg_has_role(current_user, c.relowner, 'MEMBER'))"
            )
        ):
            raise ValueError("Accounting ingress requires a non-owner database role.")
    return AccountingOutcomeIngress(
        authenticator=authenticator,
        consumer=SqlAlchemyAccountingOutcomeConsumer(
            session_factory=sessions,
            clock=clock or SystemClock(),
            transactional_dispatcher=transactional_dispatcher
            or InProcessTransactionalEventDispatcher(),
            post_commit_bus=post_commit_bus or InProcessPostCommitEventBus(),
        ),
    )
