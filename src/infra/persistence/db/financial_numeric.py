from __future__ import annotations

from enum import Enum

from sqlalchemy import Numeric

from src.core.platform.finance.precision import (
    EXCHANGE_RATE_STORAGE,
    MONEY_STORAGE,
    PERCENTAGE_STORAGE,
    QUANTITY_STORAGE,
    RATE_STORAGE,
    NumericPrecision,
)


class FinancialNumericKind(str, Enum):
    MONEY = "money"
    RATE = "rate"
    QUANTITY = "quantity"
    PERCENTAGE = "percentage"
    EXCHANGE_RATE = "exchange_rate"


_PRECISION_BY_KIND: dict[FinancialNumericKind, NumericPrecision] = {
    FinancialNumericKind.MONEY: MONEY_STORAGE,
    FinancialNumericKind.RATE: RATE_STORAGE,
    FinancialNumericKind.QUANTITY: QUANTITY_STORAGE,
    FinancialNumericKind.PERCENTAGE: PERCENTAGE_STORAGE,
    FinancialNumericKind.EXCHANGE_RATE: EXCHANGE_RATE_STORAGE,
}


def financial_numeric(kind: FinancialNumericKind | str) -> Numeric:
    """Build the canonical SQLAlchemy decimal type for a financial value."""
    resolved_kind = FinancialNumericKind(kind)
    precision = _PRECISION_BY_KIND[resolved_kind]
    return Numeric(precision.precision, precision.scale, asdecimal=True)


def financial_numeric_info(kind: FinancialNumericKind | str) -> dict[str, str]:
    """Return the schema marker enforced on project-finance decimal columns."""
    resolved_kind = FinancialNumericKind(kind)
    return {"financial_numeric": resolved_kind.value}


def precision_for(kind: FinancialNumericKind | str) -> NumericPrecision:
    return _PRECISION_BY_KIND[FinancialNumericKind(kind)]


__all__ = [
    "FinancialNumericKind",
    "financial_numeric",
    "financial_numeric_info",
    "precision_for",
]
