from __future__ import annotations

from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.platform.integration.cross_module_reference import (
    CrossModuleReference,
    ResolvedReference,
)
from src.core.platform.integration.events import IntegrationEventEnvelope
from src.core.platform.integration.delivery import (
    InboxProcessingStatus,
    IntegrationInboxReceipt,
    IntegrationOutboxRecord,
    OutboxDeliveryStatus,
)
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver

__all__ = [
    "CrossModuleReference",
    "IntegrationEventEnvelope",
    "InboxProcessingStatus",
    "IntegrationInboxReceipt",
    "IntegrationOutboxRecord",
    "OutboxDeliveryStatus",
    "IntegrationResolver",
    "ModuleRegistry",
    "ResolvedReference",
    "canonical_json_sha256",
]
