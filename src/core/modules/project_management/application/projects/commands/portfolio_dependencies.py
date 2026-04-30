from __future__ import annotations

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.portfolio import PortfolioProjectDependency
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events


class PortfolioDependencyCommandMixin:
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


__all__ = ["PortfolioDependencyCommandMixin"]
