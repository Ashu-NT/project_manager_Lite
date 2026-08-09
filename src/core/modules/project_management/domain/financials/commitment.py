from __future__ import annotations

from dataclasses import field, fields, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance import (
    EXCHANGE_RATE_STORAGE,
    MONEY_STORAGE,
    QUANTITY_STORAGE,
    RATE_STORAGE,
    CurrencyCode,
    Money,
)


class ProjectCommitmentLineState(str, Enum):
    SENT = "sent"
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ProjectCommitmentMatchKind(str, Enum):
    MATCH = "match"
    REVERSAL = "reversal"


_ALLOWED_STATE_TRANSITIONS = {
    ProjectCommitmentLineState.SENT: {
        ProjectCommitmentLineState.SENT,
        ProjectCommitmentLineState.PARTIALLY_RECEIVED,
        ProjectCommitmentLineState.FULLY_RECEIVED,
        ProjectCommitmentLineState.CLOSED,
        ProjectCommitmentLineState.CANCELLED,
    },
    ProjectCommitmentLineState.PARTIALLY_RECEIVED: {
        ProjectCommitmentLineState.PARTIALLY_RECEIVED,
        ProjectCommitmentLineState.FULLY_RECEIVED,
        ProjectCommitmentLineState.CLOSED,
        ProjectCommitmentLineState.CANCELLED,
    },
    ProjectCommitmentLineState.FULLY_RECEIVED: {
        ProjectCommitmentLineState.FULLY_RECEIVED,
        ProjectCommitmentLineState.CLOSED,
    },
    ProjectCommitmentLineState.CLOSED: {ProjectCommitmentLineState.CLOSED},
    ProjectCommitmentLineState.CANCELLED: {ProjectCommitmentLineState.CANCELLED},
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _required(value: object, *, field_name: str) -> str:
    return normalize_required_text(
        value,
        message=f"{field_name.replace('_', ' ').title()} is required.",
        code=f"PROJECT_COMMITMENT_{field_name.upper()}_REQUIRED",
    )


def _aware_utc(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(
            f"{field_name.replace('_', ' ').title()} must be a valid timestamp.",
            code=f"PROJECT_COMMITMENT_{field_name.upper()}_INVALID",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _currency(value: object) -> str:
    currency = CurrencyCode(str(value or ""))
    currency.minor_unit_quantum()
    return currency.code


@validated_dataclass
class ProjectCommitment:
    """PM-owned projection header for one authoritative purchase order."""

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    purchase_order_id: str
    purchase_order_number: str
    supplier_party_id: str
    site_id: str
    created_by: str
    created_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "purchase_order_id",
        "purchase_order_number",
        "supplier_party_id",
        "site_id",
        "created_by",
        mode="before",
    )
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_created_at(cls, value: object) -> datetime:
        return _aware_utc(value, field_name="created_at")

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        purchase_order_id: str,
        purchase_order_number: str,
        supplier_party_id: str,
        site_id: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> ProjectCommitment:
        return cls(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            purchase_order_id=purchase_order_id,
            purchase_order_number=purchase_order_number,
            supplier_party_id=supplier_party_id,
            site_id=site_id,
            created_by=actor_id,
            created_at=occurred_at,
        )


@validated_dataclass
class ProjectCommitmentLine:
    """Current financial projection for one versioned purchase-order line."""

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    commitment_id: str
    purchase_order_line_id: str
    cost_code_id: str
    state: ProjectCommitmentLineState
    ordered_quantity: Decimal
    quantity_unit: str
    unit_price: Decimal
    amount: Decimal
    currency_code: str
    base_amount: Decimal
    base_currency_code: str
    exchange_rate: Decimal
    exchange_rate_date: date
    exchange_rate_source: str
    exchange_rate_captured_at: datetime
    source_revision: int
    source_content_hash: str
    source_idempotency_key: str
    matched_amount: Decimal = Decimal("0")
    task_id: str | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    source_requisition_id: str | None = None
    source_requisition_line_id: str | None = None
    row_version: int = 1
    created_by: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_by: str = ""
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "commitment_id",
        "purchase_order_line_id",
        "cost_code_id",
        "quantity_unit",
        "exchange_rate_source",
        "source_content_hash",
        "source_idempotency_key",
        "created_by",
        "updated_by",
        mode="before",
    )
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator(
        "task_id", "source_requisition_id", "source_requisition_line_id", mode="before"
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("ordered_quantity", mode="before")
    @classmethod
    def _validate_quantity(cls, value: object) -> Decimal:
        quantity = QUANTITY_STORAGE.validate(value)
        if quantity <= 0:
            raise ValidationError(
                "Commitment quantity must be positive.",
                code="PROJECT_COMMITMENT_QUANTITY_INVALID",
            )
        return quantity

    @field_validator("unit_price", mode="before")
    @classmethod
    def _validate_unit_price(cls, value: object) -> Decimal:
        rate = RATE_STORAGE.validate(value)
        if rate < 0:
            raise ValidationError(
                "Commitment unit price cannot be negative.",
                code="PROJECT_COMMITMENT_UNIT_PRICE_INVALID",
            )
        return rate

    @field_validator("amount", "base_amount", "matched_amount", mode="before")
    @classmethod
    def _validate_money_amounts(cls, value: object, info) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount < 0:
            raise ValidationError(
                f"Commitment {info.field_name.replace('_', ' ')} cannot be negative.",
                code="PROJECT_COMMITMENT_AMOUNT_INVALID",
            )
        return amount

    @field_validator("currency_code", "base_currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        return _currency(value)

    @field_validator("exchange_rate", mode="before")
    @classmethod
    def _validate_exchange_rate(cls, value: object) -> Decimal:
        rate = EXCHANGE_RATE_STORAGE.validate(value)
        if rate <= 0:
            raise ValidationError(
                "Commitment exchange rate must be positive.",
                code="PROJECT_COMMITMENT_EXCHANGE_RATE_INVALID",
            )
        return rate

    @field_validator("source_revision", "row_version", mode="before")
    @classmethod
    def _validate_positive_versions(cls, value: object, info) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Commitment {info.field_name.replace('_', ' ')} must be a positive integer.",
                code="PROJECT_COMMITMENT_VERSION_INVALID",
            ) from exc
        if resolved < 1:
            raise ValidationError(
                f"Commitment {info.field_name.replace('_', ' ')} must be a positive integer.",
                code="PROJECT_COMMITMENT_VERSION_INVALID",
            )
        return resolved

    @field_validator("exchange_rate_captured_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_timestamps(cls, value: object, info) -> datetime:
        return _aware_utc(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_financial_snapshot(self) -> ProjectCommitmentLine:
        if self.matched_amount > self.amount:
            raise ValidationError(
                "Matched commitment amount cannot exceed committed amount.",
                code="PROJECT_COMMITMENT_OVERMATCHED",
            )
        if self.currency_code == self.base_currency_code and (
            self.exchange_rate != Decimal("1") or self.base_amount != self.amount
        ):
            raise ValidationError(
                "Identity-currency commitment snapshots must preserve amount at rate 1.",
                code="PROJECT_COMMITMENT_IDENTITY_RATE_INVALID",
            )
        return self

    @property
    def money(self) -> Money:
        return Money.of(self.amount, self.currency_code)

    @property
    def matched_money(self) -> Money:
        return Money.of(self.matched_amount, self.currency_code)

    @property
    def remaining_money(self) -> Money:
        if self.state in {
            ProjectCommitmentLineState.CLOSED,
            ProjectCommitmentLineState.CANCELLED,
        }:
            return Money.zero(self.currency_code)
        return Money.of(self.amount - self.matched_amount, self.currency_code)

    def apply_source_revision(
        self,
        *,
        state: ProjectCommitmentLineState,
        ordered_quantity: Decimal,
        unit_price: Decimal,
        amount: Decimal,
        base_amount: Decimal,
        exchange_rate: Decimal,
        exchange_rate_date: date,
        exchange_rate_source: str,
        exchange_rate_captured_at: datetime,
        source_revision: int,
        source_content_hash: str,
        source_idempotency_key: str,
        task_id: str | None,
        order_date: date | None,
        expected_delivery_date: date | None,
        source_requisition_id: str | None,
        source_requisition_line_id: str | None,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        if source_revision <= self.source_revision:
            raise BusinessRuleError(
                "Commitment source revisions must be applied in increasing order.",
                code="PROJECT_COMMITMENT_SOURCE_OUT_OF_ORDER",
            )
        if state not in _ALLOWED_STATE_TRANSITIONS[self.state]:
            raise BusinessRuleError(
                f"Commitment state cannot move from {self.state.value} to {state.value}.",
                code="PROJECT_COMMITMENT_STATE_REGRESSION",
            )
        if MONEY_STORAGE.validate(amount) < self.matched_amount:
            raise BusinessRuleError(
                "A source revision cannot reduce commitment below its matched actuals.",
                code="PROJECT_COMMITMENT_AMOUNT_BELOW_MATCHED",
            )
        candidate = replace(
            self,
            state=state,
            ordered_quantity=ordered_quantity,
            unit_price=unit_price,
            amount=amount,
            base_amount=base_amount,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=normalize_required_text(
                exchange_rate_source,
                message="Exchange rate source is required.",
                code="PROJECT_COMMITMENT_EXCHANGE_RATE_SOURCE_REQUIRED",
            ),
            exchange_rate_captured_at=_aware_utc(
                exchange_rate_captured_at, field_name="exchange_rate_captured_at"
            ),
            source_revision=source_revision,
            source_content_hash=_required(
                source_content_hash, field_name="source_content_hash"
            ),
            source_idempotency_key=_required(
                source_idempotency_key, field_name="source_idempotency_key"
            ),
            task_id=normalize_optional_identifier(task_id),
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            source_requisition_id=normalize_optional_identifier(source_requisition_id),
            source_requisition_line_id=normalize_optional_identifier(
                source_requisition_line_id
            ),
            updated_by=_required(actor_id, field_name="updated_by"),
            updated_at=_aware_utc(occurred_at, field_name="updated_at"),
        )
        for item in fields(self):
            object.__setattr__(self, item.name, getattr(candidate, item.name))

    def apply_match(self, amount: Money, *, actor_id: str, occurred_at: datetime) -> None:
        if amount.currency.code != self.currency_code or amount.amount <= 0:
            raise ValidationError(
                "Commitment matches require a positive amount in the commitment currency.",
                code="PROJECT_COMMITMENT_MATCH_MONEY_INVALID",
            )
        if self.matched_amount + amount.amount > self.amount:
            raise BusinessRuleError(
                "Matched actuals cannot exceed the committed amount.",
                code="PROJECT_COMMITMENT_OVERMATCHED",
            )
        self.matched_amount += amount.amount
        self.updated_by = _required(actor_id, field_name="updated_by")
        self.updated_at = _aware_utc(occurred_at, field_name="updated_at")

    def reverse_match(self, amount: Money, *, actor_id: str, occurred_at: datetime) -> None:
        if amount.currency.code != self.currency_code or amount.amount <= 0:
            raise ValidationError(
                "Match reversals require a positive amount in the commitment currency.",
                code="PROJECT_COMMITMENT_MATCH_REVERSAL_MONEY_INVALID",
            )
        if amount.amount > self.matched_amount:
            raise BusinessRuleError(
                "Match reversal cannot exceed the currently matched amount.",
                code="PROJECT_COMMITMENT_MATCH_REVERSAL_EXCESS",
            )
        self.matched_amount -= amount.amount
        self.updated_by = _required(actor_id, field_name="updated_by")
        self.updated_at = _aware_utc(occurred_at, field_name="updated_at")


@validated_dataclass
class ProjectCommitmentSourceRevision:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    commitment_line_id: str
    source_revision: int
    source_content_hash: str
    source_idempotency_key: str
    snapshot_json: str
    observed_at: datetime

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "commitment_line_id",
        "source_content_hash",
        "source_idempotency_key",
        "snapshot_json",
        mode="before",
    )
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator("source_revision", mode="before")
    @classmethod
    def _validate_revision(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Commitment source revision must be positive.",
                code="PROJECT_COMMITMENT_VERSION_INVALID",
            )
        return resolved

    @field_validator("observed_at", mode="before")
    @classmethod
    def _normalize_observed_at(cls, value: object) -> datetime:
        return _aware_utc(value, field_name="observed_at")


@validated_dataclass
class ProjectCommitmentMatch:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    commitment_line_id: str
    cost_entry_id: str
    kind: ProjectCommitmentMatchKind
    amount: Decimal
    currency_code: str
    idempotency_key: str
    created_by: str
    created_at: datetime
    reverses_match_id: str | None = None

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "commitment_line_id",
        "cost_entry_id",
        "idempotency_key",
        "created_by",
        mode="before",
    )
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator("reverses_match_id", mode="before")
    @classmethod
    def _normalize_reversal_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount == 0:
            raise ValidationError(
                "Commitment match amount cannot be zero.",
                code="PROJECT_COMMITMENT_MATCH_AMOUNT_INVALID",
            )
        return amount

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        return _currency(value)

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_created_at(cls, value: object) -> datetime:
        return _aware_utc(value, field_name="created_at")

    @model_validator(mode="after")
    def _validate_sign(self) -> ProjectCommitmentMatch:
        if self.kind == ProjectCommitmentMatchKind.MATCH and (
            self.amount <= 0 or self.reverses_match_id is not None
        ):
            raise ValidationError(
                "Original commitment matches must be positive and cannot reverse another match.",
                code="PROJECT_COMMITMENT_MATCH_SIGN_INVALID",
            )
        if self.kind == ProjectCommitmentMatchKind.REVERSAL and (
            self.amount >= 0 or self.reverses_match_id is None
        ):
            raise ValidationError(
                "Commitment match reversals must be negative and reference the original match.",
                code="PROJECT_COMMITMENT_MATCH_SIGN_INVALID",
            )
        return self


__all__ = [
    "ProjectCommitment",
    "ProjectCommitmentLine",
    "ProjectCommitmentLineState",
    "ProjectCommitmentMatch",
    "ProjectCommitmentMatchKind",
    "ProjectCommitmentSourceRevision",
]
