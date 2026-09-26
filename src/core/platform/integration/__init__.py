from __future__ import annotations

from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.platform.integration.cross_module_reference import (
    CrossModuleReference,
    ResolvedReference,
)
from src.core.platform.integration.delivery import (
    InboxProcessingStatus,
    IntegrationInboxReceipt,
    IntegrationOutboxRecord,
    OutboxDeliveryStatus,
)
from src.core.platform.integration.events import IntegrationEventEnvelope
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.procurement_events import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)
from src.core.platform.integration.resolver import IntegrationResolver
from src.core.platform.integration.time_events import (
    APPROVED_TIME_ENTRY_EVENT_TYPE,
    ApprovedTimeEntryEventPayload,
)

__all__ = [
    "APPROVED_TIME_ENTRY_EVENT_TYPE",
    "PROCUREMENT_COMMITMENT_EVENT_TYPE",
    "PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE",
    "ApprovedTimeEntryEventPayload",
    "CrossModuleReference",
    "InboxProcessingStatus",
    "IntegrationEventEnvelope",
    "IntegrationInboxReceipt",
    "IntegrationOutboxRecord",
    "IntegrationResolver",
    "ModuleRegistry",
    "OutboxDeliveryStatus",
    "ProcurementCommitmentEventPayload",
    "ProcurementReceiptAccrualEventPayload",
    "ResolvedReference",
    "canonical_json_sha256",
]
