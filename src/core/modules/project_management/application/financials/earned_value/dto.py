from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EvmSeriesPoint:
    period_end: date
    PV: Decimal | None
    EV: Decimal | None
    AC: Decimal | None
    BAC: Decimal | None
    CPI: Decimal | None
    SPI: Decimal | None


@dataclass(frozen=True, slots=True)
class EarnedValueMetrics:
    as_of: date
    baseline_id: str | None
    currency_code: str
    availability: str
    unavailable_reason: str | None

    BAC: Decimal | None
    PV: Decimal | None
    EV: Decimal | None
    AC: Decimal | None

    CV: Decimal | None
    SV: Decimal | None
    CPI: Decimal | None
    SPI: Decimal | None
    EAC: Decimal | None
    ETC: Decimal | None
    VAC: Decimal | None
    TCPI_to_BAC: Decimal | None = None
    TCPI_to_EAC: Decimal | None = None
    notes: str | None = None


__all__ = ['EarnedValueMetrics', 'EvmSeriesPoint']
