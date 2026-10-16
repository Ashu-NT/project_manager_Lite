"""Financial-period catalog and normal-posting queries."""

from __future__ import annotations

from datetime import date, datetime

import src.core.platform.application.finance.mappers.financial_period as response_mapper
from src.core.platform.application.finance.dto.responses.financial_period import (
    FinancialPeriodDto,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.repositories.finance import FinancialPeriodRepository
from src.core.platform.domain.finance.periods import (
    FinancialPeriod,
    FinancialPeriodStatus,
)


class FinancialPeriodQueryHandler:
    """Scoped reads, including posting checks for authenticated integrations."""

    def __init__(
        self,
        *,
        period_repo: FinancialPeriodRepository,
        user_session=None,
    ) -> None:
        self._period_repo = period_repo
        self._user_session = user_session

    def list_periods(
        self,
        *,
        fiscal_year: int | None = None,
        status: FinancialPeriodStatus | str | None = None,
    ) -> list[FinancialPeriodDto]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list financial periods",
        )
        try:
            resolved_status = FinancialPeriodStatus(status) if status is not None else None
        except ValueError as exc:
            raise ValidationError(
                "Financial period status is invalid.",
                code="FINANCIAL_PERIOD_STATUS_INVALID",
            ) from exc
        return [response_mapper.serialize(row) for row in (self._period_repo.list(
            fiscal_year=fiscal_year,
            status=resolved_status,
        ))]

    def get_period(self, period_id: str) -> FinancialPeriodDto:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view financial period",
        )
        return response_mapper.serialize(self._require_period(period_id))

    def require_open_period_for_date(self, posting_date: date) -> FinancialPeriod:
        """Resolve and validate the period used by a normal financial posting."""
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="resolve financial posting period",
        )
        return self._resolve_open_period_for_date(posting_date)

    def require_open_period_for_integration(self, posting_date: date) -> FinancialPeriod:
        """Resolve an open period for an already-authenticated trusted consumer."""
        return self._resolve_open_period_for_date(posting_date)

    def _resolve_open_period_for_date(self, posting_date: date) -> FinancialPeriod:
        if not isinstance(posting_date, date) or isinstance(posting_date, datetime):
            raise ValidationError(
                "Posting date must be a valid date.",
                code="FINANCIAL_PERIOD_DATE_INVALID",
            )
        period = self._period_repo.find_for_date(posting_date)
        if period is None:
            raise BusinessRuleError(
                "No financial period is configured for the posting date.",
                code="FINANCIAL_PERIOD_NOT_CONFIGURED",
            )
        period.require_normal_posting()
        return period

    def _require_period(self, period_id: str) -> FinancialPeriod:
        period = self._period_repo.get(period_id)
        if period is None:
            raise NotFoundError(
                "Financial period not found.",
                code="FINANCIAL_PERIOD_NOT_FOUND",
            )
        return period
__all__ = ["FinancialPeriodQueryHandler"]
