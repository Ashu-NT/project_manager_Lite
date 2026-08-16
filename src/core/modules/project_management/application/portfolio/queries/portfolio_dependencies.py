from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.pagination import PaginatedResult
from src.core.modules.project_management.contracts.reads.sorting import ReadSort, ReadSortDirection
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioProjectDependencyView,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission

_DEPENDENCY_BROWSE_SORT_KEYS = {
    "predecessorProjectName",
    "successorProjectName",
    "dependencyType",
    "createdAt",
    "updatedAt",
}


class PortfolioDependencyQueryMixin:
    def list_project_dependencies(
        self,
        *,
        heatmap_rows: list[PortfolioExecutiveRow] | None = None,
    ) -> list[PortfolioProjectDependencyView]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio project dependencies")
        accessible_projects = {project.id: project for project in self._accessible_projects()}
        if not accessible_projects:
            return []
        heatmap_by_project = {
            row.project_id: row
            for row in (heatmap_rows if heatmap_rows is not None else self.list_portfolio_heatmap())
        }
        rows: list[PortfolioProjectDependencyView] = []
        self._active_portfolio_organization_id(operation_label="view portfolio dependencies")
        for dependency in self._dependency_repo.list():
            predecessor = accessible_projects.get(dependency.predecessor_project_id)
            successor = accessible_projects.get(dependency.successor_project_id)
            if predecessor is None or successor is None:
                continue
            predecessor_heat = heatmap_by_project.get(predecessor.id)
            successor_heat = heatmap_by_project.get(successor.id)
            rows.append(
                PortfolioProjectDependencyView(
                    dependency_id=dependency.id,
                    predecessor_project_id=predecessor.id,
                    predecessor_project_name=predecessor.name,
                    predecessor_project_status=getattr(predecessor.status, "value", str(predecessor.status)),
                    successor_project_id=successor.id,
                    successor_project_name=successor.name,
                    successor_project_status=getattr(successor.status, "value", str(successor.status)),
                    dependency_type=dependency.dependency_type,
                    summary=dependency.summary,
                    pressure_label=self._combine_dependency_pressure(
                        predecessor_heat.pressure_label if predecessor_heat is not None else "Stable",
                        successor_heat.pressure_label if successor_heat is not None else "Stable",
                    ),
                    created_at=dependency.created_at,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                -self._dependency_pressure_rank(row.pressure_label),
                row.successor_project_name.lower(),
                row.predecessor_project_name.lower(),
                row.created_at,
            ),
        )

    def list_project_dependencies_page(
        self,
        *,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PaginatedResult[PortfolioProjectDependencyView]:
        """Authoritative server-paginated Dependencies browse. Predecessor/
        successor project name and status come straight from the reader's
        SQL join (no second unbounded project fetch). Pressure is display-
        only and is computed only for the projects referenced on this page —
        never a full-heatmap-scope computation, and never a sortable key
        here (see PortfolioExecutiveQueryMixin.list_portfolio_heatmap_page)."""
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio project dependencies")
        self._active_portfolio_organization_id(operation_label="view portfolio dependencies")
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys=_DEPENDENCY_BROWSE_SORT_KEYS,
            default_key="updatedAt",
            default_direction=ReadSortDirection.DESCENDING,
        )
        page_result = self._dependency_repo.list_page(
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort=sort,
        )
        referenced_project_ids = tuple(
            {
                project_id
                for item in page_result.items
                for project_id in (
                    item.dependency.predecessor_project_id,
                    item.dependency.successor_project_id,
                )
            }
        )
        pressure_by_project: dict[str, str] = {}
        if referenced_project_ids:
            scope = self._tenant_context_service.require_active_scope_ids(
                operation_label="view portfolio project dependencies"
            )
            facts = self._heatmap_reader.read_facts(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_ids=referenced_project_ids,
                as_of=date.today(),
            )
            pressure_by_project = {
                row.project_id: row.pressure_label for row in self._compute_heatmap_rows(facts)
            }
        views = [
            PortfolioProjectDependencyView(
                dependency_id=item.dependency.id,
                predecessor_project_id=item.dependency.predecessor_project_id,
                predecessor_project_name=item.predecessor_project_name,
                predecessor_project_status=item.predecessor_project_status,
                successor_project_id=item.dependency.successor_project_id,
                successor_project_name=item.successor_project_name,
                successor_project_status=item.successor_project_status,
                dependency_type=item.dependency.dependency_type,
                summary=item.dependency.summary,
                pressure_label=self._combine_dependency_pressure(
                    pressure_by_project.get(item.dependency.predecessor_project_id, "Stable"),
                    pressure_by_project.get(item.dependency.successor_project_id, "Stable"),
                ),
                created_at=item.dependency.created_at,
            )
            for item in page_result.items
        ]
        return PaginatedResult(
            items=views,
            page=page_result.page,
            page_size=page_result.page_size,
            total=page_result.total,
        )

    @staticmethod
    def _combine_dependency_pressure(predecessor_pressure: str, successor_pressure: str) -> str:
        labels = {str(predecessor_pressure or "").strip(), str(successor_pressure or "").strip()}
        if "Hot" in labels:
            return "Hot"
        if "Watch" in labels:
            return "Watch"
        if "Needs Schedule" in labels:
            return "Needs Schedule"
        return "Stable"

    @staticmethod
    def _dependency_pressure_rank(label: str) -> int:
        if label == "Hot":
            return 3
        if label == "Watch":
            return 2
        if label == "Needs Schedule":
            return 1
        return 0


__all__ = ["PortfolioDependencyQueryMixin"]
