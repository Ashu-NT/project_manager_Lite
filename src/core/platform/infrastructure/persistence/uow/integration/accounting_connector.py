from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import SqlAlchemyAuditRepository
from src.core.platform.infrastructure.persistence.repositories.integration.accounting_connector import SqlAlchemyAccountingConnectorRepository
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase, SqlAlchemyUnitOfWorkFactoryBase


class SqlAlchemyAccountingConnectorUnitOfWork(SqlAlchemyUnitOfWorkBase):
    def __init__(self, *, tenant_context_service, user_session, **kwargs):
        super().__init__(**kwargs)
        self.accounting_connectors = SqlAlchemyAccountingConnectorRepository(self._session)
        self.accounting_connectors._tenant_context_service = tenant_context_service
        audit = SqlAlchemyAuditRepository(self._session)
        audit._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=self._session, audit_repo=audit, user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyAccountingConnectorUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    def __init__(self, *, tenant_context_service, user_session, **kwargs):
        super().__init__(**kwargs)
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context):
        session = self._session_factory()
        configure_session_rls_context(session, user_session=self._user_session)
        return SqlAlchemyAccountingConnectorUnitOfWork(
            session=session, context=context,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            tenant_context_service=self._tenant_context_service, user_session=self._user_session,
        )
