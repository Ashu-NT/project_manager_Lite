from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceLedgerRow,
)
from src.core.modules.project_management.application.financials.services.finance_service import (
    FinanceService,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.enums import CostType
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class EACMethod(str, Enum):
    MANUAL = "manual"
    BAC_OVER_CPI = "bac_over_cpi"
    AC_PLUS_ETC_AT_PLAN = "ac_etc_plan"
    AC_PLUS_ETC_AT_CPI = "ac_etc_cpi"


@dataclass
class CommitmentSummary:
    project_id: str
    planned_total: float
    uncommitted_total: float
    committed_total: float
    invoiced_total: float
    paid_total: float
    actual_total: float

    @property
    def exposure(self) -> float:
        return max(0.0, self.committed_total - self.actual_total)

    @property
    def commitment_rate(self) -> float:
        return 0.0 if self.planned_total <= 0 else min(1.0, self.committed_total / self.planned_total)


@dataclass
class MaterialRollup:
    project_id: str
    task_id: str | None
    planned: float
    committed: float
    actual: float
    forecast: float
    items: list[FinanceLedgerRow] = field(default_factory=list)

    @property
    def variance(self) -> float:
        return self.forecast - self.planned


@dataclass
class CostForecastResult:
    project_id: str
    method: EACMethod
    bac: float
    ac: float
    ev: float
    etc: float
    eac: float
    vac: float
    cpi: float
    exceeds_threshold: bool = False
    threshold_percent: float = 10.0

    @property
    def is_over_budget(self) -> bool:
        return self.eac > self.bac


class ForecastCostService(ProjectManagementModuleGuardMixin):
    """Forecast calculations over the canonical finance snapshot."""

    def __init__(
        self,
        finance_service: FinanceService,
        project_repo: ProjectRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._finance = finance_service
        self._projects = project_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _require_read(self, project_id: str, operation_label: str) -> None:
        require_permission(self._user_session, "finance.read", operation_label=operation_label)
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label=operation_label
        )

    def get_commitment_summary(self, project_id: str) -> CommitmentSummary:
        self._require_read(project_id, "view commitment summary")
        snapshot = self._finance.get_finance_snapshot(project_id)
        return CommitmentSummary(
            project_id=project_id,
            planned_total=snapshot.planned,
            uncommitted_total=max(0.0, snapshot.planned - snapshot.committed),
            committed_total=snapshot.committed,
            invoiced_total=snapshot.actual,
            paid_total=snapshot.actual,
            actual_total=snapshot.actual,
        )

    def get_material_rollup(
        self, project_id: str, task_id: str | None = None
    ) -> MaterialRollup:
        self._require_read(project_id, "view material rollup")
        rows = [
            row
            for row in self._finance.list_cost_ledger(project_id)
            if row.cost_type == CostType.MATERIAL.value
            and (task_id is None or row.task_id == task_id)
            and row.included_in_policy
        ]
        planned = sum(row.amount for row in rows if row.stage == "planned")
        committed = sum(row.amount for row in rows if row.stage == "committed")
        actual = sum(row.amount for row in rows if row.stage == "actual")
        return MaterialRollup(
            project_id=project_id,
            task_id=task_id,
            planned=planned,
            committed=committed,
            actual=actual,
            forecast=max(planned, committed, actual),
            items=rows,
        )

    def compute_forecast(
        self,
        project_id: str,
        percent_complete: float,
        method: EACMethod = EACMethod.BAC_OVER_CPI,
        threshold_percent: float = 10.0,
    ) -> CostForecastResult:
        self._require_read(project_id, "compute cost forecast")
        if self._projects.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        snapshot = self._finance.get_finance_snapshot(project_id)
        bac = snapshot.planned
        ac = snapshot.actual
        pct = max(0.0, min(1.0, percent_complete))
        ev = bac * pct
        cpi = ev / ac if ac > 0 else 0.0
        etc, eac = self._compute_etc_eac(method, bac, ac, ev, cpi)
        return CostForecastResult(
            project_id=project_id,
            method=method,
            bac=bac,
            ac=ac,
            ev=ev,
            etc=etc,
            eac=eac,
            vac=bac - eac,
            cpi=cpi,
            exceeds_threshold=(bac > 0 and eac > bac * (1.0 + threshold_percent / 100.0)),
            threshold_percent=threshold_percent,
        )

    def check_cost_threshold(
        self, project_id: str, forecast_eac: float, threshold_percent: float = 10.0
    ) -> bool:
        self._require_read(project_id, "check cost threshold")
        bac = self._finance.get_finance_snapshot(project_id).planned
        return bac > 0 and forecast_eac > bac * (1.0 + threshold_percent / 100.0)

    @staticmethod
    def _compute_etc_eac(
        method: EACMethod, bac: float, ac: float, ev: float, cpi: float
    ) -> tuple[float, float]:
        if method == EACMethod.BAC_OVER_CPI:
            eac = bac / cpi if cpi > 0 else bac
            return eac - ac, eac
        if method == EACMethod.AC_PLUS_ETC_AT_PLAN:
            etc = max(0.0, bac - ev)
            return etc, ac + etc
        if method == EACMethod.AC_PLUS_ETC_AT_CPI:
            remaining = max(0.0, bac - ev)
            etc = remaining / cpi if cpi > 0 else remaining
            return etc, ac + etc
        etc = max(0.0, bac - ac)
        return etc, ac + etc


__all__ = [
    "CommitmentSummary",
    "CostForecastResult",
    "EACMethod",
    "ForecastCostService",
    "MaterialRollup",
]
