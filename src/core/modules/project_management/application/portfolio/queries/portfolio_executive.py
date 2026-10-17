from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import cast

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PaginatedResult,
)
from src.core.modules.project_management.application.portfolio.dto.responses.capacity import (
    PortfolioCapacityResourceDto,
)
from src.core.modules.project_management.application.portfolio.mappers.capacity import (
    map_capacity_pool,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_heatmap import (
    PortfolioHeatmapCalculator,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
)
from src.core.modules.project_management.application.resources.portfolio.queries.resource_pool import (
    PortfolioResourcePoolQueryHandler,
)
from src.core.modules.project_management.contracts.reads.portfolio.heatmap_reader import (
    PortfolioHeatmapReader,
)
from src.core.modules.project_management.contracts.reads.projects.catalog_reader import (
    ProjectCatalogReader,
)
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.domain.enums import (
    ProjectStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioRecentAction,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)

logger = logging.getLogger(__name__)

# Matches the existing watchlist convention used by the Dashboard's own
# top_n tables (critical_watchlist / milestone_health) — see
# ui_qml/modules/project_management/presenters/dashboard/builders/operational_table_builder.py.
TOP_AT_RISK_PROJECTS_LIMIT = 8

_HEATMAP_BROWSE_SORT_KEYS = {"projectName", "statusLabel"}


def _audit_action_label(action: str) -> str:
    action_name = str(action or "").strip()
    if not action_name:
        return "Update"
    return action_name.replace(".", " ").replace("_", " ").title()


def _audit_summary(row) -> str:
    details = dict(getattr(row, "details", {}) or {})
    for key in ("note", "status", "title", "summary", "message"):
        value = str(details.get(key) or "").strip()
        if value:
            return value
    entity_type = str(getattr(row, "entity_type", "") or "record").replace("_", " ")
    return f"{entity_type.title()} updated."



class PortfolioExecutiveQueryHandler(ProjectManagementModuleGuardMixin):
    """Executive heatmap / top-at-risk / recent-action reads over the
    authorized project scope."""

    def __init__(
        self,
        *,
        heatmap_reader: PortfolioHeatmapReader,
        heatmap_calculator: PortfolioHeatmapCalculator,
        audit_repo: AuditRepository,
        policy: PortfolioPolicy,
        tenant_context_service: TenantContextService,
        project_catalog_reader: ProjectCatalogReader | None = None,
        resource_pool_query: PortfolioResourcePoolQueryHandler | None = None,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._heatmap_reader = heatmap_reader
        self._heatmap_calculator = heatmap_calculator
        self._audit_repo = audit_repo
        self._policy = policy
        self._tenant_context_service = tenant_context_service
        self._project_catalog_reader = project_catalog_reader
        self._resource_pool_query = resource_pool_query
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def query_capacity_pool(self) -> tuple[PortfolioCapacityResourceDto, ...]:
        if self._resource_pool_query is None:
            return ()
        today = date.today()  # noqa: DTZ011
        report = self._resource_pool_query.get_pool_report(
            from_date=today, to_date=today + timedelta(days=90)
        )
        return map_capacity_pool(report)

    def list_portfolio_heatmap(self, *, limit: int | None = None) -> list[PortfolioExecutiveRow]:
        """Authoritative heatmap ranking over the COMPLETE accessible project
        scope. With limit=None (default) this returns every accessible
        project and is what list_project_dependencies() enriches against —
        do not change that default. Pass limit= to use this as the bounded
        "Top At-Risk Projects" projection (collection_semantics=top_n);
        that ranking is always computed from the full scope, never from a
        paginated page, so page_size can never change which projects appear.
        """
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view portfolio executive heatmap"
        )
        accessible_project_ids = tuple(project.id for project in self._policy.accessible_projects())
        facts = self._heatmap_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_ids=accessible_project_ids,
            as_of=date.today(),  # noqa: DTZ011 - local business date (unchanged)
        )
        rows = sorted(
            self._heatmap_calculator.compute_rows(facts),
            key=lambda row: (-row.pressure_score, -row.late_tasks, row.project_name.lower()),
        )
        if limit is not None:
            rows = rows[: max(0, int(limit))]
        return rows

    def list_top_at_risk_projects(
        self, *, limit: int = TOP_AT_RISK_PROJECTS_LIMIT
    ) -> list[PortfolioExecutiveRow]:
        """Bounded/top_n analytical projection: ranks pressure across the
        complete authorized project scope, then truncates. Never derive this
        from a paginated Heatmap page."""
        return self.list_portfolio_heatmap(limit=limit)

    def list_portfolio_heatmap_page(
        self,
        *,
        search_text: str = "",
        status: ProjectStatus | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> PaginatedResult[PortfolioExecutiveRow]:
        """Authoritative server-paginated Heatmap browse. Project selection
        (scope/search/status/sort/page) happens in SQL via the shared
        project catalog reader BEFORE any per-project pressure computation
        runs — pressure is computed only for the rows on the returned page,
        never for the full accessible scope. Sorting is restricted to
        genuinely SQL-authoritative columns (project name/status); pressure
        is display-only here and is never a sortable key for this method —
        use list_top_at_risk_projects() for a global pressure ranking.
        """
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        if self._project_catalog_reader is None:
            raise BusinessRuleError(
                "Portfolio heatmap pagination requires a project catalog reader.",
                code="PORTFOLIO_HEATMAP_PAGE_READER_REQUIRED",
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view portfolio executive heatmap"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(sorted(self._user_session.project_ids_for("project.read")))
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys=_HEATMAP_BROWSE_SORT_KEYS,
            default_key="projectName",
        )
        project_page = self._project_catalog_reader.read_page(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            finance_allowed_project_ids=(),
            search_text=search_text,
            status=status,
            page=page,
            page_size=page_size,
            sort=sort,
        )
        page_project_ids = tuple(item.project.id for item in project_page.items)
        if not page_project_ids:
            return PaginatedResult(items=[], page=page, page_size=page_size, total=project_page.filtered_total)
        facts = self._heatmap_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_ids=page_project_ids,
            as_of=date.today(),  # noqa: DTZ011 - local business date (unchanged)
        )
        rows_by_id = {row.project_id: row for row in self._heatmap_calculator.compute_rows(facts)}
        # Preserve the SQL-determined order — never re-sort by pressure here.
        ordered_rows = [rows_by_id[project_id] for project_id in page_project_ids if project_id in rows_by_id]
        return PaginatedResult(
            items=ordered_rows,
            page=page,
            page_size=page_size,
            total=project_page.filtered_total,
        )

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        require_permission(self._user_session, "portfolio.read", operation_label="view recent pm actions")
        accessible_projects = {project.id: project for project in self._policy.accessible_projects()}
        if not accessible_projects:
            return []
        _PM_ENTITY_TYPES = {
            "project", "task", "project_baseline", "approval_request",
            "timesheet_period", "project_membership", "portfolio",
        }
        rows = []
        for row in self._audit_repo.list_recent(limit=max(limit * 4, 50)):
            entity_type = str(getattr(row, "entity_type", "") or "").strip().lower()
            if entity_type not in _PM_ENTITY_TYPES:
                continue
            project_id = str(
                getattr(row, "project_id", None)
                or getattr(row, "entity_parent_id", None)
                or (getattr(row, "metadata", None) or {}).get("project_id")
                or ""
            ).strip()
            project = accessible_projects.get(project_id)
            if project is None:
                continue
            action = str(
                getattr(row, "action", None)
                or (getattr(row, "metadata", None) or {}).get("action")
                or f"{entity_type}.{getattr(row, 'operation', 'update')}"
            )
            rows.append(
                PortfolioRecentAction(
                    occurred_at=cast(
                        datetime,
                        getattr(row, "occurred_at", None) or getattr(row, "timestamp", None),
                    ),
                    project_name=project.name,
                    action_label=_audit_action_label(action),
                    actor_username=str(getattr(row, "actor_username", "") or ""),
                    summary=_audit_summary(row),
                )
            )
            if len(rows) >= limit:
                break
        return rows

    def get_executive_snapshot(self, dependencies):
        from src.core.modules.project_management.application.portfolio.dto.responses.executive import (
            PortfolioExecutiveSnapshot,
        )

        heatmap_rows = self.list_portfolio_heatmap()
        dependency_rows = dependencies.list_project_dependencies(heatmap_rows=heatmap_rows)
        return PortfolioExecutiveSnapshot(
            heatmap=tuple(heatmap_rows), dependencies=tuple(dependency_rows),
            top_at_risk_projects=tuple(heatmap_rows[:TOP_AT_RISK_PROJECTS_LIMIT]),
            hot_project_count=sum(1 for row in heatmap_rows if row.pressure_label == "Hot"),
            dependency_count=len(dependency_rows),
        )

    @staticmethod
    def empty_snapshot():
        from src.core.modules.project_management.application.portfolio.dto.responses.executive import (
            PortfolioExecutiveSnapshot,
        )

        return PortfolioExecutiveSnapshot()

    @staticmethod
    def empty_page(*, page: int, page_size: int) -> PaginatedResult:
        return PaginatedResult(items=[], page=page, page_size=page_size, total=0)



__all__ = [
    "TOP_AT_RISK_PROJECTS_LIMIT",
    "PortfolioExecutiveQueryHandler",
]
