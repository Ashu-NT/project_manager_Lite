from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from src.core.platform.common.exceptions import ValidationError

from ._decimal import canonical_decimal_text
from .currency import CurrencyCode
from .money import Money
from .quantity import DecimalQuantity, MonetaryRate, normalize_unit


class _CanonicalFinancialPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @staticmethod
    def _decimal_text(value: object, *, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be canonical decimal text")
        try:
            return canonical_decimal_text(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def _currency_text(value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("currency must be an ISO 4217 string")
        try:
            return CurrencyCode(value).code
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc


class MoneyPayload(_CanonicalFinancialPayload):
    amount: str
    currency: str

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> str:
        return cls._decimal_text(value, field_name="amount")

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        return cls._currency_text(value)

    @classmethod
    def from_domain(cls, value: Money) -> MoneyPayload:
        return cls(amount=canonical_decimal_text(value.amount), currency=value.currency.code)

    def to_domain(self) -> Money:
        return Money.of(self.amount, self.currency)


class DecimalQuantityPayload(_CanonicalFinancialPayload):
    value: str
    unit: str

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, value: object) -> str:
        return cls._decimal_text(value, field_name="value")

    @field_validator("unit", mode="before")
    @classmethod
    def _validate_unit(cls, value: object) -> str:
        try:
            return normalize_unit(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @classmethod
    def from_domain(cls, value: DecimalQuantity) -> DecimalQuantityPayload:
        return cls(value=canonical_decimal_text(value.value), unit=value.unit)

    def to_domain(self) -> DecimalQuantity:
        return DecimalQuantity.of(self.value, self.unit)


class MonetaryRatePayload(_CanonicalFinancialPayload):
    amount: str
    currency: str
    per_unit: str

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> str:
        return cls._decimal_text(value, field_name="amount")

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        return cls._currency_text(value)

    @field_validator("per_unit", mode="before")
    @classmethod
    def _validate_per_unit(cls, value: object) -> str:
        try:
            return normalize_unit(value)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    @classmethod
    def from_domain(cls, value: MonetaryRate) -> MonetaryRatePayload:
        return cls(
            amount=canonical_decimal_text(value.money.amount),
            currency=value.money.currency.code,
            per_unit=value.per_unit,
        )

    def to_domain(self) -> MonetaryRate:
        return MonetaryRate(Money.of(self.amount, self.currency), self.per_unit)


__all__ = ["DecimalQuantityPayload", "MonetaryRatePayload", "MoneyPayload"]
