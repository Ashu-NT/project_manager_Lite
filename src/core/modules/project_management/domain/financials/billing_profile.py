from __future__ import annotations

from dataclasses import field
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
from src.core.platform.finance import MONEY_STORAGE, PERCENTAGE_STORAGE, CurrencyCode


class BillingProfileStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class BillingScheduleLineStatus(str, Enum):
    PLANNED = "planned"
    READY = "ready"
    BILLED = "billed"
    CANCELLED = "cancelled"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@validated_dataclass
class ProjectBillingProfile:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    currency_code: str
    contract_reference: str
    contract_value: Decimal
    customer_party_id: str | None = None
    external_customer_reference: str | None = None
    purchase_order_reference: str | None = None
    cost_plus_markup_percent: Decimal = Decimal("0")
    payment_terms_days: int = 30
    retention_years: int = 7
    legal_hold: bool = False
    status: BillingProfileStatus = BillingProfileStatus.DRAFT
    row_version: int = 1
    created_by: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_by: str = ""
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "created_by",
        mode="before",
    )
    @classmethod
    def _required_identifiers(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"BILLING_PROFILE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("contract_reference", mode="before")
    @classmethod
    def _contract_reference(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Contract reference is required.",
            code="BILLING_PROFILE_CONTRACT_REFERENCE_REQUIRED",
        )

    @field_validator("customer_party_id", mode="before")
    @classmethod
    def _customer_party_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(
        "external_customer_reference", "purchase_order_reference", mode="before"
    )
    @classmethod
    def _optional_references(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("currency_code", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("contract_value", mode="before")
    @classmethod
    def _contract_value(cls, value: object) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount < 0:
            raise ValidationError(
                "Contract value cannot be negative.",
                code="BILLING_PROFILE_CONTRACT_VALUE_INVALID",
            )
        return amount

    @field_validator("cost_plus_markup_percent", mode="before")
    @classmethod
    def _markup(cls, value: object) -> Decimal:
        markup = PERCENTAGE_STORAGE.validate(value)
        if markup < 0 or markup > Decimal("1000"):
            raise ValidationError(
                "Cost-plus markup must be between 0 and 1000 percent.",
                code="BILLING_PROFILE_MARKUP_INVALID",
            )
        return markup

    @field_validator("payment_terms_days", mode="before")
    @classmethod
    def _payment_terms(cls, value: object) -> int:
        days = int(value)
        if days < 0 or days > 3650:
            raise ValidationError(
                "Payment terms must be between 0 and 3650 days.",
                code="BILLING_PROFILE_PAYMENT_TERMS_INVALID",
            )
        return days

    @field_validator("retention_years", mode="before")
    @classmethod
    def _retention_years(cls, value: object) -> int:
        years = int(value)
        if years < 7 or years > 100:
            raise ValidationError(
                "Billing retention must be between 7 and 100 years.",
                code="BILLING_PROFILE_RETENTION_INVALID",
            )
        return years

    @field_validator("row_version", mode="before")
    @classmethod
    def _version(cls, value: object) -> int:
        version = int(value)
        if version < 1:
            raise ValidationError(
                "Billing profile version must be positive.",
                code="BILLING_PROFILE_VERSION_INVALID",
            )
        return version

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"BILLING_PROFILE_{info.field_name.upper()}_INVALID")

    @model_validator(mode="after")
    def _external_customer_pair(self) -> "ProjectBillingProfile":
        if self.external_customer_reference and not self.customer_party_id:
            raise ValidationError(
                "An external customer reference requires a customer Party.",
                code="BILLING_PROFILE_EXTERNAL_CUSTOMER_PARTY_REQUIRED",
            )
        return self

    def activate(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status not in {BillingProfileStatus.DRAFT, BillingProfileStatus.ON_HOLD}:
            raise BusinessRuleError(
                "Only draft or on-hold billing profiles can be activated.",
                code="BILLING_PROFILE_ACTIVATION_INVALID",
            )
        if not self.customer_party_id or self.contract_value <= 0:
            raise BusinessRuleError(
                "An active billing profile requires a customer and positive contract value.",
                code="BILLING_PROFILE_ACTIVATION_INCOMPLETE",
            )
        self.status = BillingProfileStatus.ACTIVE
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def place_on_hold(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status is not BillingProfileStatus.ACTIVE:
            raise BusinessRuleError(
                "Only an active billing profile can be placed on hold.",
                code="BILLING_PROFILE_HOLD_INVALID",
            )
        self.status = BillingProfileStatus.ON_HOLD
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def close(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status not in {BillingProfileStatus.ACTIVE, BillingProfileStatus.ON_HOLD}:
            raise BusinessRuleError(
                "Only active or on-hold billing profiles can be closed.",
                code="BILLING_PROFILE_CLOSE_INVALID",
            )
        self.status = BillingProfileStatus.CLOSED
        self.updated_by = actor_id
        self.updated_at = occurred_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        currency_code: str,
        contract_reference: str,
        contract_value: Decimal,
        created_by: str,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectBillingProfile":
        now = created_at or _utc_now()
        return ProjectBillingProfile(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            currency_code=currency_code,
            contract_reference=contract_reference,
            contract_value=contract_value,
            created_by=created_by,
            updated_by=created_by,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class ProjectBillingScheduleLine:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    name: str
    amount: Decimal
    currency_code: str
    due_date: date
    task_id: str | None = None
    acceptance_reference: str | None = None
    status: BillingScheduleLineStatus = BillingScheduleLineStatus.PLANNED
    row_version: int = 1
    created_by: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_by: str = ""
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "billing_profile_id",
        "created_by", mode="before",
    )
    @classmethod
    def _required_ids(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"BILLING_SCHEDULE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Billing schedule line name is required.",
            code="BILLING_SCHEDULE_NAME_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _task_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("acceptance_reference", mode="before")
    @classmethod
    def _acceptance_reference(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, value: object) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount <= 0:
            raise ValidationError(
                "Billing schedule amount must be positive.",
                code="BILLING_SCHEDULE_AMOUNT_INVALID",
            )
        return amount

    @field_validator("currency_code", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("row_version", mode="before")
    @classmethod
    def _version(cls, value: object) -> int:
        version = int(value)
        if version < 1:
            raise ValidationError(
                "Billing schedule version must be positive.",
                code="BILLING_SCHEDULE_VERSION_INVALID",
            )
        return version

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"BILLING_SCHEDULE_{info.field_name.upper()}_INVALID")

    def mark_ready(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status is not BillingScheduleLineStatus.PLANNED:
            raise BusinessRuleError(
                "Only a planned billing schedule line can be marked ready.",
                code="BILLING_SCHEDULE_READY_INVALID",
            )
        self.status = BillingScheduleLineStatus.READY
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def mark_billed(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status is not BillingScheduleLineStatus.READY:
            raise BusinessRuleError(
                "Only a ready billing schedule line can be marked billed.",
                code="BILLING_SCHEDULE_BILLED_INVALID",
            )
        self.status = BillingScheduleLineStatus.BILLED
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def cancel(self, *, actor_id: str, occurred_at: datetime) -> None:
        if self.status not in {
            BillingScheduleLineStatus.PLANNED,
            BillingScheduleLineStatus.READY,
        }:
            raise BusinessRuleError(
                "Only a planned or ready billing schedule line can be cancelled.",
                code="BILLING_SCHEDULE_CANCEL_INVALID",
            )
        self.status = BillingScheduleLineStatus.CANCELLED
        self.updated_by = actor_id
        self.updated_at = occurred_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        billing_profile_id: str,
        name: str,
        amount: Decimal,
        currency_code: str,
        due_date: date,
        created_by: str,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectBillingScheduleLine":
        now = created_at or _utc_now()
        return ProjectBillingScheduleLine(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            billing_profile_id=billing_profile_id,
            name=name,
            amount=amount,
            currency_code=currency_code,
            due_date=due_date,
            created_by=created_by,
            updated_by=created_by,
            created_at=now,
            updated_at=now,
            **values,
        )


__all__ = [
    "BillingProfileStatus",
    "BillingScheduleLineStatus",
    "ProjectBillingProfile",
    "ProjectBillingScheduleLine",
]
