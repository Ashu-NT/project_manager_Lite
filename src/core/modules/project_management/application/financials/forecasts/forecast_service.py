from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.cost import CommitmentStatus, CostItem
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)


class EACMethod(str, Enum):
    MANUAL = "manual"                   # EAC = AC + sum(forecast_amount on remaining items)
    BAC_OVER_CPI = "bac_over_cpi"       # EAC = BAC / CPI
    AC_PLUS_ETC_AT_PLAN = "ac_etc_plan" # EAC = AC + (BAC - EV)
    AC_PLUS_ETC_AT_CPI = "ac_etc_cpi"   # EAC = AC + (BAC - EV) / CPI


@dataclass
class CommitmentSummary:
    """Snapshot of cost commitment lifecycle totals for a project."""
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
        if self.planned_total <= 0:
            return 0.0
        return min(1.0, self.committed_total / self.planned_total)


@dataclass
class MaterialRollup:
    """Aggregated material cost figures for a project or specific task."""
    project_id: str
    task_id: str | None
    planned: float
    committed: float
    actual: float
    forecast: float
    items: list[CostItem] = field(default_factory=list)

    @property
    def variance(self) -> float:
        return self.forecast - self.planned


@dataclass
class CostForecastResult:
    """ETC/EAC forecast result for a project."""
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
    """
    Financial model expansion service: committed costs, ETC/EAC forecasting,
    material roll-up, and cost threshold detection.
    """

    def __init__(
        self,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._costs: CostRepository = cost_repo
        self._projects: ProjectRepository = project_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_commitment_summary(self, project_id: str) -> CommitmentSummary:
        require_permission(self._user_session, "report.view", operation_label="view commitment summary")
        require_project_permission(
            self._user_session, project_id, "report.view",
            operation_label="view commitment summary",
        )
        items = self._costs.list_by_project(project_id)
        return self._build_commitment_summary(project_id, items)

    def get_material_rollup(
        self,
        project_id: str,
        task_id: str | None = None,
    ) -> MaterialRollup:
        require_permission(self._user_session, "report.view", operation_label="view material rollup")
        require_project_permission(
            self._user_session, project_id, "report.view",
            operation_label="view material rollup",
        )
        all_items = self._costs.list_by_project(project_id)
        material = [
            c for c in all_items
            if c.cost_type == CostType.MATERIAL
            and (task_id is None or c.task_id == task_id)
        ]
        planned = sum(c.planned_amount for c in material)
        committed = sum(c.committed_amount for c in material)
        actual = sum(c.actual_amount for c in material)
        forecast = sum(c.effective_forecast for c in material)
        return MaterialRollup(
            project_id=project_id,
            task_id=task_id,
            planned=planned,
            committed=committed,
            actual=actual,
            forecast=forecast,
            items=material,
        )

    def compute_forecast(
        self,
        project_id: str,
        percent_complete: float,
        method: EACMethod = EACMethod.BAC_OVER_CPI,
        threshold_percent: float = 10.0,
    ) -> CostForecastResult:
        require_permission(self._user_session, "report.view", operation_label="compute cost forecast")
        require_project_permission(
            self._user_session, project_id, "report.view",
            operation_label="compute cost forecast",
        )
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        items = self._costs.list_by_project(project_id)
        bac = sum(c.planned_amount for c in items)
        ac = sum(c.actual_amount for c in items)
        pct = max(0.0, min(1.0, percent_complete))
        ev = bac * pct
        cpi = (ev / ac) if ac > 0 else 0.0

        etc, eac = self._compute_etc_eac(method, bac, ac, ev, cpi, items)
        vac = bac - eac
        threshold = bac * (1.0 + threshold_percent / 100.0)
        exceeds = eac > threshold if bac > 0 else False

        return CostForecastResult(
            project_id=project_id,
            method=method,
            bac=bac,
            ac=ac,
            ev=ev,
            etc=etc,
            eac=eac,
            vac=vac,
            cpi=cpi,
            exceeds_threshold=exceeds,
            threshold_percent=threshold_percent,
        )

    def check_cost_threshold(
        self,
        project_id: str,
        forecast_eac: float,
        threshold_percent: float = 10.0,
    ) -> bool:
        require_permission(self._user_session, "report.view", operation_label="check cost threshold")
        require_project_permission(
            self._user_session, project_id, "report.view",
            operation_label="check cost threshold",
        )
        items = self._costs.list_by_project(project_id)
        bac = sum(c.planned_amount for c in items)
        if bac <= 0:
            return False
        return forecast_eac > bac * (1.0 + threshold_percent / 100.0)

    def _build_commitment_summary(
        self, project_id: str, items: list[CostItem]
    ) -> CommitmentSummary:
        uncommitted = sum(
            c.planned_amount for c in items
            if c.commitment_status == CommitmentStatus.UNCOMMITTED
        )
        committed = sum(
            c.committed_amount for c in items
            if c.commitment_status == CommitmentStatus.COMMITTED
        )
        invoiced = sum(
            c.committed_amount for c in items
            if c.commitment_status == CommitmentStatus.INVOICED
        )
        paid = sum(
            c.actual_amount for c in items
            if c.commitment_status == CommitmentStatus.PAID
        )
        planned = sum(c.planned_amount for c in items)
        actual = sum(c.actual_amount for c in items)
        return CommitmentSummary(
            project_id=project_id,
            planned_total=planned,
            uncommitted_total=uncommitted,
            committed_total=committed,
            invoiced_total=invoiced,
            paid_total=paid,
            actual_total=actual,
        )

    def _compute_etc_eac(
        self,
        method: EACMethod,
        bac: float,
        ac: float,
        ev: float,
        cpi: float,
        items: list[CostItem],
    ) -> tuple[float, float]:
        if method == EACMethod.MANUAL:
            etc = max(0.0, sum(c.effective_forecast - c.actual_amount for c in items))
            eac = ac + etc
        elif method == EACMethod.BAC_OVER_CPI:
            eac = (bac / cpi) if cpi > 0 else bac
            etc = eac - ac
        elif method == EACMethod.AC_PLUS_ETC_AT_PLAN:
            etc = max(0.0, bac - ev)
            eac = ac + etc
        elif method == EACMethod.AC_PLUS_ETC_AT_CPI:
            remaining_work = max(0.0, bac - ev)
            etc = (remaining_work / cpi) if cpi > 0 else remaining_work
            eac = ac + etc
        else:
            etc = max(0.0, bac - ac)
            eac = bac
        return etc, eac


__all__ = [
    "CommitmentSummary",
    "CostForecastResult",
    "EACMethod",
    "ForecastCostService",
    "MaterialRollup",
]
