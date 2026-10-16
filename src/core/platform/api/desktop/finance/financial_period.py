from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.finance import (
    FinancialPeriodCommandHandler,
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.finance.dto.commands.financial_periods import (
    FinancialPeriodCreateCommand,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.application.finance.dto.responses.financial_period import (
    FinancialPeriodDto,
)


class FinancialPeriodDesktopApi:
    """Desktop transport adapter over injected command and query authority."""

    def __init__(
        self,
        *,
        financial_period_commands: FinancialPeriodCommandHandler,
        financial_period_queries: FinancialPeriodQueryHandler,
    ) -> None:
        self._financial_period_commands = financial_period_commands
        self._financial_period_queries = financial_period_queries

    def list_periods(
        self,
        *,
        fiscal_year: int | None = None,
        status: str | None = None,
    ) -> DesktopApiResult[tuple[FinancialPeriodDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                period
                for period in self._financial_period_queries.list_periods(
                    fiscal_year=fiscal_year,
                    status=status,
                )
            )
        )

    def get_period(self, period_id: str) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._financial_period_queries.get_period(period_id)
        )

    def create_period(
        self,
        command: FinancialPeriodCreateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._financial_period_commands.create_period(command)
        )

    def update_period(
        self,
        command: FinancialPeriodUpdateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._financial_period_commands.update_period(command)
        )

    def close_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._financial_period_commands.close_period(command)
        )

    def lock_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._financial_period_commands.lock_period(command)
        )



__all__ = ["FinancialPeriodDesktopApi"]
