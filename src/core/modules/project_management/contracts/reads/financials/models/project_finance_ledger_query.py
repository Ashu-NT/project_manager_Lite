"""Bounded ledger detail requests; totals always describe the full scoped set."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectFinanceLedgerQuery:
    offset: int = 0
    limit: int = 100

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("Finance ledger offset must be non-negative.")
        if not 1 <= self.limit <= 500:
            raise ValueError("Finance ledger limit must be between 1 and 500.")
