from __future__ import annotations

from src.core.platform.api.desktop.finance.models import (
    FinancialPeriodDto,
)
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
                self._serialize(period)
                for period in self._financial_period_queries.list_periods(
                    fiscal_year=fiscal_year,
                    status=status,
                )
            )
        )

    def get_period(self, period_id: str) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_queries.get_period(period_id)
            )
        )

    def create_period(
        self,
        command: FinancialPeriodCreateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_commands.create_period(command)
            )
        )

    def update_period(
        self,
        command: FinancialPeriodUpdateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_commands.update_period(command)
            )
        )

    def close_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_commands.close_period(command)
            )
        )

    def lock_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_commands.lock_period(command)
            )
        )

    @staticmethod
    def _serialize(period) -> FinancialPeriodDto:
        return FinancialPeriodDto(
            id=period.id,
            organization_id=period.organization_id,
            code=period.code,
            name=period.name,
            fiscal_year=period.fiscal_year,
            period_number=period.period_number,
            start_date=period.start_date.isoformat(),
            end_date=period.end_date.isoformat(),
            status=period.status.value,
            accepts_normal_posting=period.accepts_normal_posting,
            closed_by=period.closed_by or "",
            closed_at=period.closed_at.isoformat() if period.closed_at else "",
            locked_by=period.locked_by or "",
            locked_at=period.locked_at.isoformat() if period.locked_at else "",
            version=period.version,
        )


__all__ = ["FinancialPeriodDesktopApi"]
