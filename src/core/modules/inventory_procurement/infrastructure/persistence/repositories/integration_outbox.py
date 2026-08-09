from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.infrastructure.persistence.orm.integration_outbox import ProcurementFinancialOutboxORM
from src.infra.persistence.repositories.integration_delivery import SqlAlchemyIntegrationOutboxRepository


class SqlAlchemyProcurementFinancialOutboxRepository(SqlAlchemyIntegrationOutboxRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, orm_type=ProcurementFinancialOutboxORM, owner_module="inventory_procurement")


__all__ = ["SqlAlchemyProcurementFinancialOutboxRepository"]
