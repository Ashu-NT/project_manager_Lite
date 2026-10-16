from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.domain.finance.periods.financial_period import (
        FinancialPeriod,
    )

from src.core.platform.application.finance.dto.responses.financial_period import (
    FinancialPeriodDto,
)


def serialize(period: FinancialPeriod) -> FinancialPeriodDto:
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
