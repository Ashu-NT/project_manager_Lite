from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode
from src.core.platform.finance.money.quantity import MonetaryRate, normalize_unit


class RateType(str, Enum):
    COST = "cost"
    BILLING = "billing"


class RateLineOrigin(str, Enum):
    CONFIGURED = "configured"
    LEGACY_SEEDED = "legacy_seeded"


class RateModifier(str, Enum):
    """A hard-worked-hour context. At most one applies to a given hour —
    these are not independent multipliers that stack."""

    OVERTIME = "overtime"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


def _snapshot_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RateSelectionSnapshot:
    """An immutable record of one ADR-PF-005 rate resolution — the
    monetary rate selected, which line/card/version produced it, and any
    modifier applied. Lives in the domain layer (not application, where
    the resolver that builds these lives) so both the resolver and the
    read/resolution contracts can depend on it without either depending
    on the other's layer."""

    monetary_rate: MonetaryRate
    rate_card_id: str
    rate_line_id: str
    rate_card_version: int
    origin: RateLineOrigin
    precedence_level: int
    effective_date: date
    modifier_applied: RateModifier | None = None
    modifier_multiplier: Decimal | None = None
    resolved_at: datetime = field(default_factory=_snapshot_utc_now)

    @property
    def modifiers_applied(self) -> Mapping[str, Decimal]:
        """Read-only view for callers that want a dict-shaped summary —
        the snapshot's real, immutable state is the two scalar fields
        above; a stored mutable dict field would let a caller mutate a
        supposedly-frozen snapshot in place."""
        if self.modifier_applied is None or self.modifier_multiplier is None:
            return MappingProxyType({})
        return MappingProxyType({self.modifier_applied.value: self.modifier_multiplier})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_identifier(value: object, *, label: str, code: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=code,
    )


@validated_dataclass
class ProjectRateCard:
    id: str
    tenant_id: str
    organization_id: str
    name: str
    project_id: str | None = None
    card_kind: str | None = None
    version: int = 1
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"RATE_CARD_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Rate card name is required.",
            code="RATE_CARD_NAME_REQUIRED",
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _normalize_project_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("card_kind", mode="before")
    @classmethod
    def _normalize_card_kind(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value).lower() or None
        if normalized is not None and normalized != "legacy":
            raise ValidationError(
                "Rate card kind must be 'legacy' or unset.",
                code="RATE_CARD_CARD_KIND_INVALID",
            )
        return normalized

    @property
    def is_legacy(self) -> bool:
        return self.card_kind == "legacy"

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Rate card version must be positive.",
                code="RATE_CARD_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"RATE_CARD_{info.field_name.upper()}_INVALID",
        )

    @property
    def is_organization_wide(self) -> bool:
        return self.project_id is None

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        name: str,
        **values,
    ) -> "ProjectRateCard":
        return ProjectRateCard(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            **values,
        )


@validated_dataclass
class RateCardLine:
    id: str
    tenant_id: str
    organization_id: str
    rate_card_id: str
    rate_type: RateType
    unit: str
    rate_amount: Decimal
    rate_currency: str
    origin: RateLineOrigin = RateLineOrigin.CONFIGURED
    resource_id: str | None = None
    customer_party_id: str | None = None
    contract_reference: str | None = None
    role: str | None = None
    skill_code: str | None = None
    department_id: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True
    overtime_multiplier: Decimal | None = None
    weekend_multiplier: Decimal | None = None
    holiday_multiplier: Decimal | None = None
    version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", "rate_card_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"RATE_CARD_LINE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("rate_type", mode="before")
    @classmethod
    def _validate_rate_type(cls, value: object) -> RateType:
        if isinstance(value, RateType):
            return value
        raw = normalize_optional_text(value).lower()
        try:
            return RateType(raw)
        except ValueError as exc:
            raise ValidationError(
                "Rate type must be 'cost' or 'billing'.",
                code="RATE_CARD_LINE_RATE_TYPE_INVALID",
            ) from exc

    @field_validator("origin", mode="before")
    @classmethod
    def _validate_origin(cls, value: object) -> RateLineOrigin:
        if isinstance(value, RateLineOrigin):
            return value
        raw = normalize_optional_text(value).lower() or RateLineOrigin.CONFIGURED.value
        try:
            return RateLineOrigin(raw)
        except ValueError as exc:
            raise ValidationError(
                "Rate line origin must be 'configured' or 'legacy_seeded'.",
                code="RATE_CARD_LINE_ORIGIN_INVALID",
            ) from exc

    @field_validator(
        "resource_id",
        "customer_party_id",
        "contract_reference",
        "department_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_identifiers(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("role", "skill_code", mode="before")
    @classmethod
    def _normalize_optional_dimensions(cls, value: object) -> str | None:
        # Canonicalized at write time (lowercase), matching this codebase's
        # established convention for controlled/catalog-like values — see
        # ResourceSkill.skill_code and TaskSkillRequirement.skill_code. This
        # is what lets the resolver compare without re-folding every read.
        normalized = normalize_optional_text(value).lower()
        return normalized or None

    @field_validator("unit", mode="before")
    @classmethod
    def _validate_unit(cls, value: object) -> str:
        return normalize_unit(value)

    @field_validator("rate_currency", mode="before")
    @classmethod
    def _validate_rate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("rate_amount", mode="before")
    @classmethod
    def _validate_rate_amount(cls, value: object) -> Decimal:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
        if resolved < 0:
            raise ValidationError(
                "Rate amount cannot be negative.",
                code="RATE_CARD_LINE_RATE_AMOUNT_INVALID",
            )
        return resolved

    @field_validator(
        "overtime_multiplier",
        "weekend_multiplier",
        "holiday_multiplier",
        mode="before",
    )
    @classmethod
    def _validate_multipliers(cls, value: object, info) -> Decimal | None:
        if value in (None, ""):
            return None
        resolved = Decimal(str(value))
        if resolved < 0:
            raise ValidationError(
                f"{info.field_name.replace('_', ' ').title()} cannot be negative.",
                code=f"RATE_CARD_LINE_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Rate card line version must be positive.",
                code="RATE_CARD_LINE_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"RATE_CARD_LINE_{info.field_name.upper()}_INVALID",
        )

    @model_validator(mode="after")
    def _validate_selection_key_shape(self) -> "RateCardLine":
        if bool(self.customer_party_id) != bool(self.contract_reference):
            raise ValidationError(
                "Customer and contract reference must be supplied together.",
                code="RATE_CARD_LINE_CUSTOMER_CONTRACT_INCOMPLETE",
            )
        if self.customer_party_id and not self.resource_id:
            raise ValidationError(
                "A customer-contract line must also identify a resource.",
                code="RATE_CARD_LINE_CUSTOMER_CONTRACT_REQUIRES_RESOURCE",
            )
        has_role_dimension = bool(self.role or self.skill_code or self.department_id)
        if self.resource_id and has_role_dimension:
            raise ValidationError(
                "A rate line matches either a specific resource or a role/skill/"
                "department dimension, never both.",
                code="RATE_CARD_LINE_SELECTION_KEY_AMBIGUOUS",
            )
        if not self.resource_id and not has_role_dimension:
            raise ValidationError(
                "A rate line must match a resource or a role/skill/department "
                "dimension.",
                code="RATE_CARD_LINE_SELECTION_KEY_REQUIRED",
            )
        if (
            self.effective_from
            and self.effective_to
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "Rate line effective end cannot be before its start.",
                code="RATE_CARD_LINE_EFFECTIVE_RANGE_INVALID",
            )
        return self

    def is_effective_on(self, value: date) -> bool:
        return (
            self.is_active
            and (self.effective_from is None or self.effective_from <= value)
            and (self.effective_to is None or value <= self.effective_to)
        )

    @property
    def specificity_dimension_count(self) -> int:
        """Number of populated role/skill/department dimensions (level 3/5 ties)."""
        return sum(1 for value in (self.role, self.skill_code, self.department_id) if value)

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        rate_card_id: str,
        rate_type: RateType | str,
        unit: str,
        rate_amount: Decimal,
        rate_currency: str,
        **values,
    ) -> "RateCardLine":
        return RateCardLine(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            rate_card_id=rate_card_id,
            rate_type=rate_type,
            unit=unit,
            rate_amount=rate_amount,
            rate_currency=rate_currency,
            **values,
        )


__all__ = [
    "ProjectRateCard",
    "RateCardLine",
    "RateLineOrigin",
    "RateModifier",
    "RateSelectionSnapshot",
    "RateType",
]
