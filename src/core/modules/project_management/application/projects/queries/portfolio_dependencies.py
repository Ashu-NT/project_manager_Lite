from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioProjectDependencyView,
)
from src.core.platform.auth.authorization import require_permission


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
        for dependency in self._dependency_repo.list_all():
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
