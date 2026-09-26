"""Authenticate before parsing; retain bounded fingerprints, never raw ingress."""

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from pydantic import SecretBytes, ValidationError

from src.core.platform.contract.port.integration.accounting_outcomes import (
    AccountingIngressAuthenticator,
    AuthenticatedAccountingConnection,
    ExternalAccountingOutcome,
)

MAX_ACCOUNTING_OUTCOME_BYTES = 16_384


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate Accounting field.")
        result[key] = value
    return result


class IngressRejectionReason(StrEnum):
    MALFORMED = "malformed_outcome"
    SCOPE_MISMATCH = "outcome_scope_mismatch"
    ORDERING_MISMATCH = "outcome_ordering_mismatch"


class AccountingIngressAuthenticationError(Exception):
    def __init__(self):
        super().__init__("Accounting ingress authentication failed.")


class AccountingIngressSizeError(Exception):
    def __init__(self):
        super().__init__("Accounting ingress exceeds the allowed size.")


@dataclass(frozen=True)
class ValidatedAccountingIngress:
    connection: AuthenticatedAccountingConnection
    body_sha256: str
    byte_count: int
    outcome: ExternalAccountingOutcome | None
    rejection: IngressRejectionReason | None


class AccountingOutcomeConsumer(Protocol):
    def consume(self, ingress: ValidatedAccountingIngress) -> object: ...


class AccountingOutcomeIngress:
    """Installed endpoint composition owns the authenticator, never a payload field.

    Oversize bodies are refused before parsing/authentication, without persistence
    under an unverified tenant. Authenticated malformed bodies reach scoped
    quarantine using only a digest/length and finite reason. Infrastructure must
    bound HTTP/queue reads before constructing these bytes as well.
    """

    def __init__(
        self,
        *,
        authenticator: AccountingIngressAuthenticator,
        consumer: AccountingOutcomeConsumer,
    ):
        self._authenticator = authenticator
        self._consumer = consumer

    def receive(self, *, body: bytes, authentication: SecretBytes):
        if not isinstance(body, bytes) or len(body) > MAX_ACCOUNTING_OUTCOME_BYTES:
            raise AccountingIngressSizeError()
        try:
            connection = self._authenticator.authenticate(
                body=body, authentication=authentication
            )
            if not isinstance(connection, AuthenticatedAccountingConnection):
                raise AccountingIngressAuthenticationError()
        except Exception:
            raise AccountingIngressAuthenticationError() from None
        reason = None
        outcome = None
        try:
            candidate = ExternalAccountingOutcome.model_validate(
                json.loads(body, object_pairs_hook=_unique_object)
            )
            if (candidate.tenant_id, candidate.organization_id) != (
                connection.tenant_id,
                connection.organization_id,
            ):
                reason = IngressRejectionReason.SCOPE_MISMATCH
            elif connection.authoritative_sequence != (candidate.sequence is not None):
                reason = IngressRejectionReason.ORDERING_MISMATCH
            else:
                outcome = candidate
        except (ValidationError, ValueError, RecursionError):
            reason = IngressRejectionReason.MALFORMED
        return self._consumer.consume(
            ValidatedAccountingIngress(
                connection=connection,
                body_sha256=sha256(body).hexdigest(),
                byte_count=len(body),
                outcome=outcome,
                rejection=reason,
            )
        )
