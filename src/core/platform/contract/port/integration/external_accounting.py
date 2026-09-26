"""External transport only; future internal Accounting consumes integration events."""

from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Protocol

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)

Identifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ExternalAccountingEvidence(BaseModel):
    """Detached transport value; exact persisted bytes, never live PM aggregates."""

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    handoff_id: Identifier
    tenant_id: Identifier
    organization_id: Identifier
    project_id: Identifier
    source_id: Identifier
    source_version: int = Field(ge=1)
    schema_name: str = Field(min_length=1, max_length=128)
    schema_version: int = Field(ge=1)
    payload_bytes: bytes = Field(strict=True, min_length=1, repr=False)
    payload_hash: Digest
    correlation_id: str | None = None
    causation_id: str | None = None

    @model_validator(mode="after")
    def verify_hash(self):
        if sha256(self.payload_bytes).hexdigest() != self.payload_hash:
            raise ValueError("Persisted Accounting evidence hash mismatch.")
        return self


class ExternalAccountingTarget(BaseModel):
    """Pinned external destination; secret material is resolved outside persistence."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tenant_id: Identifier
    organization_id: Identifier
    adapter_id: Identifier
    connection_id: Identifier
    configuration_version: int = Field(ge=1)


class ExternalAccountingReceipt(BaseModel):
    """Durable transport acceptance only, not invoice or business acknowledgement."""

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    handoff_id: Identifier
    payload_hash: Digest
    source_version: int = Field(ge=1)
    adapter_id: Identifier
    connection_id: Identifier
    remote_reference: str = Field(min_length=1, max_length=512, repr=False)
    accepted_at: AwareDatetime

    def matches(
        self, evidence: ExternalAccountingEvidence, target: ExternalAccountingTarget
    ) -> bool:
        return (
            self.handoff_id == evidence.handoff_id
            and self.payload_hash == evidence.payload_hash
            and self.source_version == evidence.source_version
            and self.adapter_id == target.adapter_id
            and self.connection_id == target.connection_id
            and evidence.tenant_id == target.tenant_id
            and evidence.organization_id == target.organization_id
        )


class ExternalAccountingFailureKind(StrEnum):
    RETRYABLE = "retryable_transport"
    PERMANENT = "permanent_rejection"
    CONFIGURATION = "configuration_blocked"
    CREDENTIAL = "credential_failure"
    AMBIGUOUS = "reconciliation_required"


class ExternalAccountingDeliveryError(Exception):
    """Only a finite category crosses the boundary; never a raw provider response."""

    def __init__(self, kind: ExternalAccountingFailureKind):
        self.kind = ExternalAccountingFailureKind(kind)
        super().__init__(self.kind.value)


class ExternalAccountingDeliveryPort(Protocol):
    # Providers must guarantee durable deduplication by handoff_id + payload_hash.
    # Unsupported providers are blocked before sending, not blindly retried.
    supports_durable_idempotency: bool

    def deliver(
        self,
        *,
        evidence: ExternalAccountingEvidence,
        target: ExternalAccountingTarget,
        credential: SecretStr,
    ) -> ExternalAccountingReceipt: ...


class AccountingCredentialProvider(Protocol):
    def resolve(
        self, *, tenant_id: str, organization_id: str, secret_reference: str
    ) -> SecretStr: ...
