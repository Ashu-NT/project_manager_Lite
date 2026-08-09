from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.orm.time_management.time_financial_outbox import TimeFinancialOutboxORM
from src.infra.persistence.repositories.integration_delivery import SqlAlchemyIntegrationOutboxRepository


class SqlAlchemyTimeFinancialOutboxRepository(SqlAlchemyIntegrationOutboxRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, orm_type=TimeFinancialOutboxORM, owner_module="platform_time")


__all__ = ["SqlAlchemyTimeFinancialOutboxRepository"]
