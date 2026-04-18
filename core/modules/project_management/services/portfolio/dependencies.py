from __future__ import annotations

from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from core.modules.project_management.domain.enums import DependencyType
from core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
)
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission


class PortfolioDependencyMixin:
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

    def create_project_dependency(
        self,
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType | str = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> PortfolioProjectDependency:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio dependency")
        accessible_projects = {project.id: project for project in self._accessible_projects()}
        predecessor = accessible_projects.get(str(predecessor_project_id or "").strip())
        successor = accessible_projects.get(str(successor_project_id or "").strip())
        if predecessor is None or successor is None:
            raise ValidationError(
                "Choose two accessible projects for the portfolio dependency.",
                code="PORTFOLIO_DEPENDENCY_PROJECT_REQUIRED",
            )
        if predecessor.id == successor.id:
            raise ValidationError(
                "Portfolio dependency must link two different projects.",
                code="PORTFOLIO_DEPENDENCY_SAME_PROJECT",
            )
        for existing in self._dependency_repo.list_all():
            if (
                existing.predecessor_project_id == predecessor.id
                and existing.successor_project_id == successor.id
            ):
                raise ValidationError(
                    "That portfolio dependency already exists.",
                    code="PORTFOLIO_DEPENDENCY_DUPLICATE",
                )
        normalized_type = (
            dependency_type
            if isinstance(dependency_type, DependencyType)
            else DependencyType(str(dependency_type or DependencyType.FINISH_TO_START.value))
        )
        dependency = PortfolioProjectDependency.create(
            predecessor_project_id=predecessor.id,
            successor_project_id=successor.id,
            dependency_type=normalized_type,
            summary=(summary or "").strip(),
        )
        self._dependency_repo.add(dependency)
        self._session.commit()
        record_audit(
            self,
            action="portfolio.project_dependency.add",
            entity_type="portfolio_project_dependency",
            entity_id=dependency.id,
            project_id=successor.id,
            details={
                "predecessor_project_id": predecessor.id,
                "predecessor_project_name": predecessor.name,
                "successor_project_id": successor.id,
                "successor_project_name": successor.name,
                "dependency_type": normalized_type.value,
                "summary": dependency.summary,
            },
        )
        domain_events.portfolio_changed.emit(dependency.id)
        return dependency

    def remove_project_dependency(self, dependency_id: str) -> None:
        require_permission(self._user_session, "portfolio.manage", operation_label="remove portfolio dependency")
        dependency = self._dependency_repo.get(dependency_id)
        if dependency is None:
            raise NotFoundError(
                "Portfolio dependency not found.",
                code="PORTFOLIO_DEPENDENCY_NOT_FOUND",
            )
        accessible_projects = {project.id: project for project in self._accessible_projects()}
        predecessor = accessible_projects.get(dependency.predecessor_project_id)
        successor = accessible_projects.get(dependency.successor_project_id)
        if predecessor is None or successor is None:
            raise ValidationError(
                "You no longer have access to one of the projects in this dependency.",
                code="PORTFOLIO_DEPENDENCY_SCOPE_INVALID",
            )
        self._dependency_repo.delete(dependency_id)
        self._session.commit()
        record_audit(
            self,
            action="portfolio.project_dependency.remove",
            entity_type="portfolio_project_dependency",
            entity_id=dependency.id,
            project_id=successor.id,
            details={
                "predecessor_project_id": predecessor.id,
                "predecessor_project_name": predecessor.name,
                "successor_project_id": successor.id,
                "successor_project_name": successor.name,
                "dependency_type": dependency.dependency_type.value,
                "summary": dependency.summary,
            },
        )
        domain_events.portfolio_changed.emit(dependency.id)

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
