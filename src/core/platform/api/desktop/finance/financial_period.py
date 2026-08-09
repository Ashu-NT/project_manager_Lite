from __future__ import annotations

from datetime import date

from src.core.platform.api.desktop.finance.models import (
    FinancialPeriodCreateCommand,
    FinancialPeriodDto,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.common.exceptions import ValidationError


def _parse_required_date(value: str, *, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be a valid ISO date.",
            code="FINANCIAL_PERIOD_DATE_INVALID",
        ) from exc


def _parse_optional_date(value: str | None, *, field_name: str) -> date | None:
    if value is None:
        return None
    return _parse_required_date(value, field_name=field_name)


class FinancialPeriodDesktopApi:
    """Desktop transport adapter; policy remains in ``FinancialPeriodService``."""

    def __init__(self, *, financial_period_service: FinancialPeriodService) -> None:
        self._financial_period_service = financial_period_service

    def list_periods(
        self,
        *,
        fiscal_year: int | None = None,
        status: str | None = None,
    ) -> DesktopApiResult[tuple[FinancialPeriodDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize(period)
                for period in self._financial_period_service.list_periods(
                    fiscal_year=fiscal_year,
                    status=status,
                )
            )
        )

    def get_period(self, period_id: str) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_service.get_period(period_id)
            )
        )

    def create_period(
        self,
        command: FinancialPeriodCreateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_service.create_period(
                    code=command.code,
                    name=command.name,
                    fiscal_year=command.fiscal_year,
                    period_number=command.period_number,
                    start_date=_parse_required_date(
                        command.start_date,
                        field_name="Start date",
                    ),
                    end_date=_parse_required_date(
                        command.end_date,
                        field_name="End date",
                    ),
                )
            )
        )

    def update_period(
        self,
        command: FinancialPeriodUpdateCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_service.update_period(
                    command.period_id,
                    expected_version=command.expected_version,
                    code=command.code,
                    name=command.name,
                    fiscal_year=command.fiscal_year,
                    period_number=command.period_number,
                    start_date=_parse_optional_date(
                        command.start_date,
                        field_name="Start date",
                    ),
                    end_date=_parse_optional_date(
                        command.end_date,
                        field_name="End date",
                    ),
                )
            )
        )

    def close_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_service.close_period(
                    command.period_id,
                    expected_version=command.expected_version,
                )
            )
        )

    def lock_period(
        self,
        command: FinancialPeriodTransitionCommand,
    ) -> DesktopApiResult[FinancialPeriodDto]:
        return execute_desktop_operation(
            lambda: self._serialize(
                self._financial_period_service.lock_period(
                    command.period_id,
                    expected_version=command.expected_version,
                )
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
