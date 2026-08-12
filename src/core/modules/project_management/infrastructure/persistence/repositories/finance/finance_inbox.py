from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import ProjectFinanceInboxORM
from src.infra.persistence.repositories.integration_delivery import SqlAlchemyIntegrationInboxRepository


class SqlAlchemyProjectFinanceInboxRepository(SqlAlchemyIntegrationInboxRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, orm_type=ProjectFinanceInboxORM)


__all__ = ["SqlAlchemyProjectFinanceInboxRepository"]
