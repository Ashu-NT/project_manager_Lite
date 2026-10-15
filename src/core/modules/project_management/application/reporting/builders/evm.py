"""Earned value report builder -- thin reporting delegate.

Point-in-time EVM delegates to the canonical Decimal EVM authority; the trend
series delegates to financials/earned_value/evm_series.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.earned_value.canonical import (
    CanonicalEarnedValueCalculator,
    EvmCalculationInput,
)
from src.core.modules.project_management.application.financials.earned_value.dto import (
    EarnedValueMetrics,
    EvmSeriesPoint,
)
from src.core.modules.project_management.application.financials.earned_value.evm_series import (
    EarnedValueSeriesCalculator,
)
from src.core.modules.project_management.application.reporting.builders.access import (
    ReportingAccessPolicy,
)
from src.core.modules.project_management.application.reporting.builders.cost_policy import (
    ReportingCostPolicy,
)
from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


class EarnedValueReportBuilder(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        access: ReportingAccessPolicy,
        cost_policy: ReportingCostPolicy,
        evm_series_reader: EvmSeriesReader,
        tenant_context_service: TenantContextService,
        calendar: CalendarProtocol,
        module_catalog_service=None,
    ) -> None:
        self._access = access
        self._cost_policy = cost_policy
        self._evm_series_reader = evm_series_reader
        self._tenant_context_service = tenant_context_service
        self._calendar = calendar
        self._user_session = access.user_session
        self._module_catalog_service = module_catalog_service

    def _make_evm_calculator(self) -> CanonicalEarnedValueCalculator:
        return CanonicalEarnedValueCalculator()

    def _make_evm_series_calculator(self) -> EarnedValueSeriesCalculator:
        return EarnedValueSeriesCalculator(
            reader=self._evm_series_reader,
            tenant_context_service=self._tenant_context_service,
            calendar=self._calendar,
            calculator=self._make_evm_calculator(),
        )

    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> EarnedValueMetrics:
        self._access.require_finance_view("view earned value report", project_id=project_id)
        resolved_as_of = as_of or date.today()  # noqa: DTZ011
        facts = self._cost_policy.read_evm_facts(
            project_id,
            baseline_id=baseline_id,
            as_of=resolved_as_of,
        )
        return self._make_evm_calculator().calculate(
            EvmCalculationInput(
                project_id=project_id,
                as_of_date=resolved_as_of,
                currency_code=facts.finance.project.currency_code,
                baseline_id=facts.baseline_id,
                baseline_tasks=facts.baseline_tasks,
                task_progress=tuple(
                    (task.task_id, task.percent_complete) for task in facts.finance.tasks
                ),
                posted_actual=facts.finance.control.posted_actual,
                approved_forecast_etc=facts.finance.control.forecast_etc,
            ),
            working_days_between=self._calendar.working_days_between,
        )

    def get_evm_series(
        self,
        project_id: str,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        self._access.require_finance_view("view earned value trend", project_id=project_id)
        return self._make_evm_series_calculator().build_series(
            project_id, baseline_id=baseline_id, as_of=as_of
        )


__all__ = ["EarnedValueReportBuilder"]
