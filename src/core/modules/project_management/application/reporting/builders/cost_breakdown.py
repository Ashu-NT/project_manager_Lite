"""Cost breakdown report builder -- thin reporting delegate.

Business logic lives in financials/cost/engines/cost_breakdown_engine.py and
the shared ``ReportingCostPolicy``.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.engines.cost_breakdown_engine import (
    CostBreakdownEngine,
)
from src.core.modules.project_management.application.financials.models import (
    CostBreakdownRow,
    CostSourceBreakdown,
)
from src.core.modules.project_management.application.reporting.builders.access import (
    ReportingAccessPolicy,
)
from src.core.modules.project_management.application.reporting.builders.cost_policy import (
    CostControlTotals,
    ReportingCostPolicy,
)


class CostBreakdownReportBuilder(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        access: ReportingAccessPolicy,
        cost_policy: ReportingCostPolicy,
        module_catalog_service=None,
    ) -> None:
        self._access = access
        self._cost_policy = cost_policy
        self._user_session = access.user_session
        self._module_catalog_service = module_catalog_service

    def get_cost_breakdown(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> list[CostBreakdownRow]:
        self._access.require_finance_view("view cost breakdown report", project_id=project_id)
        resolved_as_of = as_of or date.today()  # noqa: DTZ011
        if baseline_id is not None:
            self._cost_policy.read_evm_facts(
                project_id, baseline_id=baseline_id, as_of=resolved_as_of,
            )
        _, policy = self._cost_policy.compose_finance_policy(project_id, as_of=resolved_as_of)
        return CostBreakdownEngine().build_breakdown_from_snapshot(policy.snapshot)

    def get_project_cost_control_totals(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostControlTotals:
        self._access.require_finance_view("view cost control totals", project_id=project_id)
        _, policy = self._cost_policy.compose_finance_policy(
            project_id,
            as_of=as_of or date.today(),  # noqa: DTZ011
        )
        return policy.totals

    def get_project_cost_source_breakdown(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostSourceBreakdown:
        self._access.require_finance_view("view cost source breakdown", project_id=project_id)
        _, policy = self._cost_policy.compose_finance_policy(
            project_id,
            as_of=as_of or date.today(),  # noqa: DTZ011
        )
        return policy.source_breakdown


__all__ = ["CostBreakdownReportBuilder"]
