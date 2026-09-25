from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.modules.project_management.gateway.billing.accounting_billing import ProjectBillingPreparationPayload
from src.core.platform.domain.finance import CurrencyCode
from src.core.platform.integration.canonical_json import canonical_json_bytes, canonical_json_sha256


class AccountingHandoffSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_name: Literal["project_accounting_handoff.v1"]
    handoff_id: str = Field(min_length=1)
    approved_preparation_version: int = Field(ge=1)
    billing_profile_version: int = Field(ge=1)
    approval_request_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    requested_at: datetime
    evidence: ProjectBillingPreparationPayload

    @model_validator(mode="after")
    def validate_evidence(self):
        evidence = self.evidence
        if evidence.message_id != self.handoff_id:
            raise ValueError("Handoff and message identities must agree.")
        if self.requested_at.tzinfo is None or evidence.approved_at.tzinfo is None:
            raise ValueError("Approval and request timestamps must be timezone-aware.")
        if not evidence.lines or evidence.period_end < evidence.period_start:
            raise ValueError("Approved billing evidence requires lines and a valid period.")
        currency = CurrencyCode(evidence.currency_code).code
        amounts = []
        line_ids = set()
        try:
            total = Decimal(evidence.total_amount)
            for line in evidence.lines:
                if line.line_id in line_ids:
                    raise ValueError("Duplicate approved line identity.")
                line_ids.add(line.line_id)
                if CurrencyCode(line.currency_code).code != currency:
                    raise ValueError("Approved line currency differs from header currency.")
                quantity, rate, amount = (Decimal(value) for value in (line.quantity, line.unit_rate, line.net_amount))
                if not all(value.is_finite() for value in (quantity, rate, amount)):
                    raise ValueError("Finite Decimal evidence is required.")
                if quantity <= 0 or rate < 0 or amount < 0:
                    raise ValueError("Invalid approved line values.")
                amounts.append(amount)
            if not total.is_finite() or total <= 0 or sum(amounts, Decimal("0")) != total:
                raise ValueError("Approved line amounts must exactly reconcile to the total.")
        except InvalidOperation as exc:
            raise ValueError("Invalid Decimal evidence.") from exc
        return self

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self)

    @property
    def content_hash(self) -> str:
        return canonical_json_sha256(self)
