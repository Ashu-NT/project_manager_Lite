from __future__ import annotations

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date, timedelta

from src.core.modules.project_management.contracts.reads.portfolio.resource_pool_reader import (
    PortfolioResourcePoolReader,
)
from src.core.modules.project_management.contracts.reads.portfolio.models.resource_pool_facts import (
    PortfolioDemandFact,
    PortfolioResourceFact,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError


@dataclass
class ResourceDemandEntry:
    resource_id: str
    resource_name: str
    project_id: str
    project_name: str
    from_date: date | None
    to_date: date | None
    total_allocation_percent: float


@dataclass
class ResourcePoolSummary:
    """
    Portfolio-level demand vs capacity summary for a single resource.
    """
    resource_id: str
    resource_name: str
    capacity_percent: float
    demands: list[ResourceDemandEntry]
    peak_load_percent: float
    average_load_percent: float
    overloaded: bool

    @property
    def total_demand_percent(self) -> float:
        return sum(d.total_allocation_percent for d in self.demands)


@dataclass
class PortfolioResourcePoolReport:
    """
    Cross-project resource demand and capacity report for a portfolio view.
    """
    from_date: date
    to_date: date
    pool: list[ResourcePoolSummary]

    @property
    def overloaded_resources(self) -> list[ResourcePoolSummary]:
        return [r for r in self.pool if r.overloaded]

    @property
    def utilization_by_resource(self) -> dict[str, float]:
        return {r.resource_id: r.average_load_percent for r in self.pool}


class PortfolioResourcePoolService:
    """
    Portfolio-level resource pool analysis.

    Shows shared resource demand across all active projects, enabling PMO-level
    capacity vs demand visibility and prioritization decisions.

    Uses one scoped capacity fact set and one working-day snapshot for
    project attribution and portfolio aggregation.
    """

    def __init__(
        self,
        reader: PortfolioResourcePoolReader,
        calendar: CalendarProtocol,
        tenant_context_service=None,
        user_session=None,
    ) -> None:
        self._reader = reader
        self._calendar = calendar
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def get_pool_report(
        self,
        from_date: date,
        to_date: date,
        resource_ids: list[str] | None = None,
    ) -> PortfolioResourcePoolReport:
        """
        Build a portfolio resource pool report for the given date range.
        If resource_ids is None, includes all active resources.
        """
        scope = self._require_scope(operation_label="build portfolio resource pool")
        facts = self._reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            from_date=from_date,
            to_date=to_date,
            resource_ids=(
                None
                if resource_ids is None
                else tuple(dict.fromkeys(str(value) for value in resource_ids if value))
            ),
        )
        working_dates = self._working_dates(from_date, to_date)
        demands_by_resource: dict[str, list[PortfolioDemandFact]] = {}
        for demand in facts.demands:
            demands_by_resource.setdefault(demand.resource_id, []).append(demand)
        summaries = [
            self._build_summary(
                resource,
                demands_by_resource.get(resource.resource_id, []),
                from_date,
                to_date,
                working_dates,
            )
            for resource in facts.resources
        ]

        return PortfolioResourcePoolReport(
            from_date=from_date,
            to_date=to_date,
            pool=summaries,
        )

    def get_resource_demand_by_project(
        self,
        resource_id: str,
        from_date: date,
        to_date: date,
    ) -> list[ResourceDemandEntry]:
        """Return per-project demand breakdown for a single resource."""
        scope = self._require_scope(operation_label="view portfolio resource demand")
        facts = self._reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            from_date=from_date,
            to_date=to_date,
            resource_ids=(str(resource_id),),
        )
        return self._build_demands(facts.demands, from_date, to_date)

    # ── internal ────────────────────────────────────────────────────────────

    def _build_summary(
        self,
        resource: PortfolioResourceFact,
        demand_facts: list[PortfolioDemandFact],
        from_date: date,
        to_date: date,
        working_dates: frozenset[date],
    ) -> ResourcePoolSummary:
        capacity = float(resource.capacity_percent or 100.0)
        if capacity <= 0:
            capacity = 100.0

        demands = self._build_demands(demand_facts, from_date, to_date)
        daily_loads = {
            day: sum(
                demand.allocation_percent
                for demand in demand_facts
                if demand.start_date <= day <= demand.end_date
            )
            for day in working_dates
        }
        peak_load = max(daily_loads.values(), default=0.0)
        average_load = (
            sum(daily_loads.values()) / len(working_dates)
            if working_dates
            else 0.0
        )

        return ResourcePoolSummary(
            resource_id=resource.resource_id,
            resource_name=resource.name,
            capacity_percent=capacity,
            demands=demands,
            peak_load_percent=peak_load,
            average_load_percent=average_load,
            overloaded=peak_load >= capacity,
        )

    def _build_demands(
        self,
        demand_facts: tuple[PortfolioDemandFact, ...] | list[PortfolioDemandFact],
        from_date: date,
        to_date: date,
    ) -> list[ResourceDemandEntry]:
        return [
            ResourceDemandEntry(
                resource_id=fact.resource_id,
                resource_name="",  # caller can look up from pool summary
                project_id=fact.project_id,
                project_name=fact.project_name,
                from_date=max(fact.start_date, from_date),
                to_date=min(fact.end_date, to_date),
                total_allocation_percent=fact.allocation_percent,
            )
            for fact in demand_facts
        ]

    def _working_dates(self, from_date: date, to_date: date) -> frozenset[date]:
        bulk_loader = getattr(self._calendar, "working_day_dates_between", None)
        if callable(bulk_loader):
            return frozenset(bulk_loader(from_date, to_date))
        current = from_date
        working: set[date] = set()
        while current <= to_date:
            if self._calendar.is_working_day(current):
                working.add(current)
            current += timedelta(days=1)
        return frozenset(working)

    def _require_scope(self, *, operation_label: str):
        """Enforce the missing application-layer guard for this cross-project report."""
        require_permission(self._user_session, "portfolio.read", operation_label=operation_label)
        tenant_context = self._tenant_context_service
        if tenant_context is None:
            raise BusinessRuleError(
                f"Active tenant and organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_scope_ids(operation_label=operation_label)


__all__ = [
    "PortfolioResourcePoolService",
    "PortfolioResourcePoolReport",
    "ResourcePoolSummary",
    "ResourceDemandEntry",
]
