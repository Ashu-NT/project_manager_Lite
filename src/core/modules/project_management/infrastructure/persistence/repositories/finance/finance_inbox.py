from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import ProjectFinanceInboxORM
from src.core.platform.integration import (
    APPROVED_TIME_ENTRY_EVENT_TYPE,
    ApprovedTimeEntryEventPayload,
    IntegrationInboxReceipt,
)
from src.infra.persistence.repositories.integration_delivery import SqlAlchemyIntegrationInboxRepository


class SqlAlchemyProjectFinanceInboxRepository(SqlAlchemyIntegrationInboxRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, orm_type=ProjectFinanceInboxORM)

    def _additional_insert_values(
        self, receipt: IntegrationInboxReceipt
    ) -> dict[str, object]:
        if receipt.envelope.event_type != APPROVED_TIME_ENTRY_EVENT_TYPE:
            return {}
        payload = ApprovedTimeEntryEventPayload.model_validate(receipt.envelope.payload)
        return {
            "source_project_id": payload.project_id,
            "source_resource_id": payload.resource_id,
            "source_work_date": payload.work_date,
            "source_revision": payload.source_revision,
        }


__all__ = ["SqlAlchemyProjectFinanceInboxRepository"]
