"""External Accounting business outcomes, never transport or monetary authority."""

from datetime import timezone
from enum import StrEnum
from typing import Annotated, Literal, Protocol

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretBytes,
    field_validator,
    model_validator,
)

from src.core.platform.contract.port.integration.external_accounting import (
    Digest,
    Identifier,
)


class AccountingOutcomeKind(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    RECONCILED = "reconciled"


class AuthenticatedAccountingConnection(BaseModel):
    """Returned by trusted authentication, NOT constructed from payload claims.

    An adapter may assert sequenced outcomes only when its remote contract supplies
    authoritative monotonic ordering. Neither arrival time nor local clocks qualify.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    tenant_id: Identifier
    organization_id: Identifier
    adapter_id: Identifier
    connection_id: Identifier
    principal_name: Identifier
    authoritative_sequence: bool = Field(strict=True)


class ExternalAccountingOutcome(BaseModel):
    """Schema v1 carries only business acknowledgement/rejection/reconciliation.

    No free-text status, invoice reference, monetary amount, project or preparation
    lookup is accepted. The local target is resolved through the persisted handoff.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    schema_name: Literal["external_accounting_outcome"]
    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)]
    external_event_id: Identifier
    tenant_id: Identifier
    organization_id: Identifier
    handoff_id: Identifier
    approved_source_version: Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
    handoff_payload_hash: Digest
    outcome: AccountingOutcomeKind
    sequence: Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)] | None
    occurred_at: AwareDatetime
    reconciliation_reference: Identifier | None = None

    @field_validator("occurred_at")
    @classmethod
    def normalize_timestamp(cls, value):
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_reconciliation(self):
        if (self.outcome is AccountingOutcomeKind.RECONCILED) != (
            self.reconciliation_reference is not None
        ):
            raise ValueError("Only reconciliation requires reconciliation evidence.")
        return self


class AccountingIngressAuthenticator(Protocol):
    """Trusted installed adapter verifies authenticity over the exact bounded bytes.

    Signature/mTLS/token verification belongs to infrastructure, not payload scope.
    Failure must raise; no anonymous or payload-derived fallback is permitted.
    Credentials must not be logged or persisted. No vendor implementation ships here.
    """

    def authenticate(
        self, *, body: bytes, authentication: SecretBytes
    ) -> AuthenticatedAccountingConnection: ...
