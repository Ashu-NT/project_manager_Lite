from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    PerformanceEvmFact,
)
from src.core.platform.common.exceptions import BusinessRuleError

logger = logging.getLogger(__name__)


class EvmQueries:
    def get_evm(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        baseline_id: str | None = None,
    ) -> PerformanceEvmFact:
        self._authorize_finance(project_id, "view earned value performance")
        resolved_as_of = as_of_date or datetime.now(timezone.utc).astimezone().date()
        basis = self._read_basis(project_id, resolved_as_of)
        return self._read_evm(
            project_id=project_id,
            as_of_date=resolved_as_of,
            basis=basis,
            baseline_id=baseline_id,
        )

    def _read_evm(
        self,
        *,
        project_id: str,
        as_of_date: date,
        basis: object,
        baseline_id: str | None,
    ) -> PerformanceEvmFact:
        try:
            metrics = self._earned_value_authority.get_earned_value(
                project_id,
                as_of=as_of_date,
                baseline_id=baseline_id,
            )
        except BusinessRuleError as exc:
            if str(getattr(exc, "code", "")) == "PERMISSION_DENIED":
                raise
            return self._unavailable_evm(
                project_id=project_id,
                as_of_date=as_of_date,
                basis=basis,
                availability=self._evm_availability(exc),
                reason=str(exc),
                baseline_id=baseline_id,
            )
        except Exception:
            logger.exception(
                "PM Performance EVM calculation unavailable project=%s as_of=%s",
                project_id,
                as_of_date,
            )
            return self._unavailable_evm(
                project_id=project_id,
                as_of_date=as_of_date,
                basis=basis,
                availability="calculator_error",
                reason="Earned value is temporarily unavailable.",
                baseline_id=baseline_id,
            )

        etc = self._optional_decimal(getattr(metrics, "ETC", None))
        return PerformanceEvmFact(
            project_id=project_id,
            as_of_date=as_of_date,
            availability=str(getattr(metrics, "availability", "available")),
            unavailable_reason=str(getattr(metrics, "unavailable_reason", "") or ""),
            baseline_id=str(getattr(metrics, "baseline_id", "") or "") or None,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            currency_code=basis.currency_code,
            bac=self._optional_decimal(getattr(metrics, "BAC", None)),
            pv=self._optional_decimal(getattr(metrics, "PV", None)),
            ev=self._optional_decimal(getattr(metrics, "EV", None)),
            ac=self._optional_decimal(getattr(metrics, "AC", None)),
            cv=self._optional_decimal(getattr(metrics, "CV", None)),
            sv=self._optional_decimal(getattr(metrics, "SV", None)),
            cpi=self._optional_decimal(getattr(metrics, "CPI", None)),
            spi=self._optional_decimal(getattr(metrics, "SPI", None)),
            etc=etc,
            eac=self._optional_decimal(getattr(metrics, "EAC", None)),
            vac=self._optional_decimal(getattr(metrics, "VAC", None)),
            tcpi_bac=self._optional_decimal(getattr(metrics, "TCPI_to_BAC", None)),
            tcpi_eac=self._optional_decimal(getattr(metrics, "TCPI_to_EAC", None)),
            notes=str(getattr(metrics, "notes", "") or ""),
        )

    @staticmethod
    def _optional_decimal(value: object) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    @staticmethod
    def _evm_availability(exc: BusinessRuleError) -> str:
        return {
            "NO_BASELINE": "baseline_unavailable",
            "BASELINE_EMPTY": "baseline_unavailable",
        }.get(str(getattr(exc, "code", "")), "prerequisite_unavailable")

    @staticmethod
    def _unavailable_evm(
        *,
        project_id: str,
        as_of_date: date,
        basis: object,
        availability: str,
        reason: str,
        baseline_id: str | None,
    ) -> PerformanceEvmFact:
        return PerformanceEvmFact(
            project_id=project_id,
            as_of_date=as_of_date,
            availability=availability,
            unavailable_reason=reason,
            baseline_id=baseline_id,
            budget_revision=getattr(basis, "approved_budget_revision", None),
            forecast_revision=getattr(basis, "approved_forecast_revision", None),
            forecast_as_of=getattr(basis, "approved_forecast_as_of", None),
            currency_code=str(getattr(basis, "currency_code", "") or ""),
            bac=None,
            pv=None,
            ev=None,
            ac=None,
            cv=None,
            sv=None,
            cpi=None,
            spi=None,
            etc=None,
            eac=None,
            vac=None,
            tcpi_bac=None,
            tcpi_eac=None,
            notes="",
        )
