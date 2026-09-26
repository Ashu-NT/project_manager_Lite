"""EVM core mixin — thin reporting delegate.

Business logic delegates to the canonical Decimal EVM authority.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.financials.earned_value.canonical import (
    CanonicalEarnedValueCalculator,
    EvmCalculationInput,
)
from src.core.modules.project_management.infrastructure.reporting.builders.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    EarnedValueMetrics,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


class ReportingEvmCoreMixin(ReportingCostPolicyMixin):
    _calendar: CalendarProtocol

    def _make_evm_calculator(self) -> CanonicalEarnedValueCalculator:
        return CanonicalEarnedValueCalculator()

    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> EarnedValueMetrics:
        self._require_finance_view("view earned value report", project_id=project_id)
        resolved_as_of = as_of or date.today()
        facts = self._read_evm_facts(
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
