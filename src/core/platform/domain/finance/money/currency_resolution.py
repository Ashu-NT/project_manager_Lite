from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.platform.common.exceptions import ValidationError

from .currency import CurrencyCode


class CurrencySource(str, Enum):
    EXPLICIT = "explicit"
    PROJECT = "project"
    ORGANIZATION = "organization"


@dataclass(frozen=True, slots=True)
class CurrencyResolution:
    currency: CurrencyCode
    source: CurrencySource


def resolve_currency_code(
    *,
    explicit: CurrencyCode | str | None = None,
    project_default: CurrencyCode | str | None = None,
    organization_default: CurrencyCode | str | None = None,
    require_minor_units: bool = True,
) -> CurrencyResolution:
    candidates = (
        (CurrencySource.EXPLICIT, explicit),
        (CurrencySource.PROJECT, project_default),
        (CurrencySource.ORGANIZATION, organization_default),
    )
    for source, value in candidates:
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        currency = CurrencyCode.parse(value)
        if require_minor_units and not currency.has_minor_unit_definition:
            raise ValidationError(
                f"Currency code '{currency.code}' has no minor-unit definition.",
                code="CURRENCY_MINOR_UNITS_UNDEFINED",
            )
        return CurrencyResolution(currency=currency, source=source)
    raise ValidationError(
        "Currency could not be resolved from explicit, project, or organization context.",
        code="CURRENCY_RESOLUTION_REQUIRED",
    )


__all__ = ["CurrencyResolution", "CurrencySource", "resolve_currency_code"]
