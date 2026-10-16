from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
)
from src.core.platform.common.exceptions import ValidationError


def command_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ValidationError(
            f"{label} must use YYYY-MM-DD.",
            code="PROJECT_FORECAST_DATE_INVALID",
        ) from exc


def optional_command_date(value: str) -> date | None:
    return command_date(value, "Forecast period date") if value else None


def command_amount(value: str) -> Decimal:
    try:
        amount = Decimal(str(value or "0").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            "Impact amount must be a canonical decimal value.",
            code="FINANCIAL_CHANGE_IMPACT_AMOUNT_INVALID",
        ) from exc
    if not amount.is_finite():
        raise ValidationError(
            "Impact amount must be finite.",
            code="FINANCIAL_CHANGE_IMPACT_AMOUNT_INVALID",
        )
    return amount


def command_impact_type(value: str) -> FinancialChangeImpactType:
    try:
        return FinancialChangeImpactType(str(value).strip().lower())
    except ValueError as exc:
        raise ValidationError(
            "Impact type must be Budget, Forecast, or Schedule.",
            code="FINANCIAL_CHANGE_IMPACT_TYPE_INVALID",
        ) from exc
