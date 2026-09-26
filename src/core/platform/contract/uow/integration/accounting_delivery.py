from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingEvidence,
    ExternalAccountingFailureKind,
    ExternalAccountingReceipt,
    ExternalAccountingTarget,
)


class ClaimedAccountingDelivery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outbox_id: str
    lease_token: str
    attempt_count: int = Field(ge=1)
    evidence: ExternalAccountingEvidence
    target: ExternalAccountingTarget | None
    secret_reference: str | None = Field(repr=False)
    preflight_failure: ExternalAccountingFailureKind | None


class AccountingDeliveryTransactions(Protocol):
    """Each call owns a fresh, scoped, committed transaction; no session escapes."""

    def claim(self) -> ClaimedAccountingDelivery | None: ...

    def finalize(
        self,
        claim: ClaimedAccountingDelivery,
        result: ExternalAccountingReceipt | ExternalAccountingFailureKind,
    ) -> None: ...
