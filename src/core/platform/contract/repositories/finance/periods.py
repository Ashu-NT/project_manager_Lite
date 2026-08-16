from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.core.platform.finance.periods import FinancialPeriod, FinancialPeriodStatus


class FinancialPeriodRepository(ABC):
    @abstractmethod
    def lock_catalog(self) -> None:
        """Serialize period-definition writes for the active organization."""
        ...

    @abstractmethod
    def add(self, period: FinancialPeriod) -> None: ...

    @abstractmethod
    def get(self, period_id: str) -> FinancialPeriod | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> FinancialPeriod | None: ...

    @abstractmethod
    def find_for_date(self, posting_date: date) -> FinancialPeriod | None: ...

    @abstractmethod
    def list(
        self,
        *,
        fiscal_year: int | None = None,
        status: FinancialPeriodStatus | None = None,
    ) -> list[FinancialPeriod]: ...

    @abstractmethod
    def overlaps(
        self,
        *,
        start_date: date,
        end_date: date,
        exclude_period_id: str | None = None,
    ) -> bool: ...

    @abstractmethod
    def update(self, period: FinancialPeriod, *, expected_version: int) -> None: ...


__all__ = ["FinancialPeriodRepository"]
