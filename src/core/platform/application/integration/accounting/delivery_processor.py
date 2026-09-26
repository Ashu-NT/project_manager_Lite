import logging
from collections.abc import Mapping
from types import MappingProxyType

from src.core.platform.contract.port.integration.external_accounting import (
    AccountingCredentialProvider,
    ExternalAccountingDeliveryError,
    ExternalAccountingDeliveryPort,
    ExternalAccountingFailureKind,
    ExternalAccountingReceipt,
)
from src.core.platform.contract.uow.integration.accounting_delivery import (
    AccountingDeliveryTransactions,
    ClaimedAccountingDelivery,
)

logger = logging.getLogger(__name__)


class ExternalAccountingDeliveryProcessor:
    """One bounded synchronous attempt; the runtime owns polling and shutdown."""

    def __init__(
        self,
        *,
        transactions: AccountingDeliveryTransactions,
        adapters: Mapping[str, ExternalAccountingDeliveryPort],
        credentials: AccountingCredentialProvider,
    ):
        self._transactions = transactions
        self._adapters = MappingProxyType(dict(adapters))
        self._credentials = credentials

    def process_one(self) -> bool:
        claim = self._transactions.claim()
        if claim is None:
            return False
        # claim() has committed and disposed its session before any provider call.
        result = self._deliver(claim)
        self._transactions.finalize(claim, result)
        logger.info(
            "Accounting transport finalized handoff_id=%s attempt=%s result=%s",
            claim.evidence.handoff_id,
            claim.attempt_count,
            "transport_accepted"
            if isinstance(result, ExternalAccountingReceipt)
            else result.value,
        )
        return True

    def _deliver(self, claim: ClaimedAccountingDelivery):
        if claim.preflight_failure is not None:
            return claim.preflight_failure
        target = claim.target
        if target is None or not claim.secret_reference:
            return ExternalAccountingFailureKind.CONFIGURATION
        if (target.tenant_id, target.organization_id) != (
            claim.evidence.tenant_id,
            claim.evidence.organization_id,
        ):
            return ExternalAccountingFailureKind.CONFIGURATION
        adapter = self._adapters.get(target.adapter_id)
        if adapter is None or adapter.supports_durable_idempotency is not True:
            return ExternalAccountingFailureKind.CONFIGURATION
        try:
            credential = self._credentials.resolve(
                tenant_id=target.tenant_id,
                organization_id=target.organization_id,
                secret_reference=claim.secret_reference,
            )
            if not credential.get_secret_value():
                return ExternalAccountingFailureKind.CREDENTIAL
        except Exception:
            # Provider exceptions may embed credentials. Never log or persist them.
            return ExternalAccountingFailureKind.CREDENTIAL
        try:
            receipt = adapter.deliver(
                evidence=claim.evidence, target=target, credential=credential
            )
        except ExternalAccountingDeliveryError as error:
            return error.kind
        except Exception:
            return ExternalAccountingFailureKind.AMBIGUOUS
        if not isinstance(receipt, ExternalAccountingReceipt) or not receipt.matches(
            claim.evidence, target
        ):
            return ExternalAccountingFailureKind.AMBIGUOUS
        return receipt
