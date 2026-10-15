"""Bounded ledger detail requests; totals always describe the full scoped set."""

from dataclasses import dataclass

from src.core.platform.common.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class ProjectFinanceLedgerQuery:
    offset: int = 0
    limit: int = 100

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValidationError("Finance ledger offset must be non-negative.", code="FINANCE_LEDGER_OFFSET_INVALID")
        if not 1 <= self.limit <= 500:
            raise ValidationError("Finance ledger limit must be between 1 and 500.", code="FINANCE_LEDGER_LIMIT_INVALID")
