from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingPreparationLine,
)
from src.core.modules.project_management.gateway.billing.accounting_billing import (
    ProjectBillingPreparationPayload,
)
from src.core.platform.domain.finance import CurrencyCode
from src.core.platform.integration.canonical_json import (
    canonical_json_bytes,
    canonical_json_sha256,
)


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
    approved_lines: tuple[ProjectBillingPreparationLine, ...]

    @field_validator("approved_lines", mode="before")
    @classmethod
    def _restore_source_timestamps(cls, values):
        # The write entity accepts datetime objects; the persisted contract is JSON.
        return tuple(
            {**value, "created_at": datetime.fromisoformat(value["created_at"])}
            if isinstance(value, dict) and isinstance(value.get("created_at"), str)
            else value
            for value in values
        )

    @model_validator(mode="after")
    def validate_evidence(self):
        evidence = self.evidence
        if evidence.message_id != self.handoff_id:
            raise ValueError("Handoff and message identities must agree.")
        if self.requested_at.tzinfo is None or evidence.approved_at.tzinfo is None:
            raise ValueError("Approval and request timestamps must be timezone-aware.")
        if not evidence.lines or evidence.period_end < evidence.period_start:
            raise ValueError(
                "Approved billing evidence requires lines and a valid period."
            )
        currency = CurrencyCode(evidence.currency_code).code
        approved = {line.id: line for line in self.approved_lines}
        if len(approved) != len(self.approved_lines) or len(approved) != len(
            evidence.lines
        ):
            raise ValueError(
                "Approved line evidence must match transport lines exactly."
            )
        amounts = []
        line_ids = set()
        try:
            total = Decimal(evidence.total_amount)
            for line in evidence.lines:
                source = approved.get(line.line_id)
                if source is None or (
                    source.tenant_id,
                    source.organization_id,
                    source.project_id,
                    source.preparation_id,
                ) != (
                    evidence.tenant_id,
                    evidence.organization_id,
                    evidence.project_id,
                    evidence.preparation_id,
                ):
                    raise ValueError("Approved source evidence scope mismatch.")
                for name in (
                    "source_id",
                    "source_revision",
                    "source_content_hash",
                    "description",
                    "source_date",
                    "unit",
                    "currency_code",
                    "task_id",
                    "resource_id",
                ):
                    if getattr(source, name) != getattr(line, name):
                        raise ValueError(
                            "Transport line must preserve approved source evidence."
                        )
                if source.source_type.value != line.source_type:
                    raise ValueError("Transport line source type mismatch.")
                if line.line_id in line_ids:
                    raise ValueError("Duplicate approved line identity.")
                line_ids.add(line.line_id)
                if CurrencyCode(line.currency_code).code != currency:
                    raise ValueError(
                        "Approved line currency differs from header currency."
                    )
                quantity, rate, amount = (
                    Decimal(value)
                    for value in (line.quantity, line.unit_rate, line.net_amount)
                )
                if not all(value.is_finite() for value in (quantity, rate, amount)):
                    raise ValueError("Finite Decimal evidence is required.")
                if quantity == 0 or amount == 0:
                    raise ValueError("Invalid approved line values.")
                if (quantity, rate, amount) != (
                    source.quantity,
                    source.unit_rate,
                    source.net_amount,
                ):
                    raise ValueError(
                        "Transport amounts must preserve approved line evidence."
                    )
                amounts.append(amount)
            if (
                not total.is_finite()
                or total == 0
                or sum(amounts, Decimal("0")) != total
            ):
                raise ValueError(
                    "Approved line amounts must exactly reconcile to the total."
                )
        except InvalidOperation as exc:
            raise ValueError("Invalid Decimal evidence.") from exc
        return self

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self)

    @property
    def content_hash(self) -> str:
        return canonical_json_sha256(self)


class AccountingHandoffRequestResult(BaseModel):
    """Local command receipt, not a transport acknowledgement or payload export."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    handoff_id: str
    preparation_id: str
    approved_preparation_version: int
    requested_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: AccountingHandoffSnapshot):
        return cls(
            handoff_id=snapshot.handoff_id,
            preparation_id=snapshot.evidence.preparation_id,
            approved_preparation_version=snapshot.approved_preparation_version,
            requested_at=snapshot.requested_at,
        )
