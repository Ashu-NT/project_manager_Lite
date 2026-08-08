"""EVM core mixin — thin reporting delegate.

Business logic lives in financials/earned_value/evm_calculator.py.
"""

from __future__ import annotations

from datetime import date

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.application.financials.earned_value.evm_calculator import (
    EarnedValueCalculator,
)
from src.core.modules.project_management.infrastructure.reporting.builders.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    EarnedValueMetrics,
)

class ReportingEvmCoreMixin(ReportingCostPolicyMixin):
    _calendar: CalendarProtocol

    def _make_evm_calculator(self) -> EarnedValueCalculator:
        return EarnedValueCalculator(
            calendar=self._calendar,
        )

    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> EarnedValueMetrics:
        self._require_view("view earned value report", project_id=project_id)
        resolved_as_of = as_of or date.today()
        facts, policy = self._compose_evm_policy(
            project_id,
            baseline_id=baseline_id,
            as_of=resolved_as_of,
        )
        if policy.snapshot.unresolved_labor_rates:
            raise BusinessRuleError(
                "Actual cost cannot be calculated because one or more labor "
                "rates could not be resolved.",
                code="ACTUAL_COST_INCOMPLETE",
            )
        return self._make_evm_calculator().calculate(
            project_id,
            as_of=resolved_as_of,
            prepared_facts=facts,
            actual_cost=policy.totals.actual,
        )
