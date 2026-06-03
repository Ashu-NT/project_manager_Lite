"""EVM core mixin — thin reporting delegate.

Business logic lives in financials/earned_value/evm_calculator.py.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
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
    _baseline_repo: BaselineRepository
    _task_repo: TaskRepository
    _calendar: CalendarProtocol
    _project_repo: ProjectRepository
    _cost_repo: CostRepository

    def _make_evm_calculator(self) -> EarnedValueCalculator:
        engine = self._make_cost_policy_engine()
        return EarnedValueCalculator(
            baseline_repo=self._baseline_repo,
            task_repo=self._task_repo,
            project_repo=self._project_repo,
            calendar=self._calendar,
            get_actual_cost=engine.get_actual_cost,
        )

    def get_earned_value(
        self,
        project_id: str,
        as_of: Optional[date] = None,
        baseline_id: Optional[str] = None,
    ) -> EarnedValueMetrics:
        self._require_view("view earned value report", project_id=project_id)
        return self._make_evm_calculator().calculate(
            project_id, as_of=as_of, baseline_id=baseline_id
        )
