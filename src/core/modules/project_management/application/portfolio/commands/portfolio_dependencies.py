from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioProjectDependencyChanged,
    PortfolioProjectDependencyChangeType,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
    new_portfolio_context,
    utc_now,
)
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioProjectDependencyRepository,
)
from src.core.modules.project_management.contracts.uow.portfolio.portfolio_unit_of_work import (
    PortfolioUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.portfolio import (
    PortfolioProjectDependency,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class PortfolioDependencyCommandHandler(ProjectManagementModuleGuardMixin):
    """Governed cross-project dependency writes (add/remove)."""

    def __init__(
        self,
        *,
        dependency_repo: PortfolioProjectDependencyRepository,
        policy: PortfolioPolicy,
        uow_factory: PortfolioUnitOfWorkFactory,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._dependency_repo = dependency_repo
        self._policy = policy
        self._uow_factory = uow_factory
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def create_project_dependency(
        self,
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType | str = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> PortfolioProjectDependency:
        require_permission(self._user_session, "portfolio.manage", operation_label="create portfolio dependency")
        accessible_projects = {project.id: project for project in self._policy.accessible_projects()}
        dependency = PortfolioProjectDependency.create(
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dependency_type,
            summary=summary,
        )
        predecessor = accessible_projects.get(dependency.predecessor_project_id)
        successor = accessible_projects.get(dependency.successor_project_id)
        if predecessor is None or successor is None:
            raise ValidationError(
                "Choose two accessible projects for the portfolio dependency.",
                code="PORTFOLIO_DEPENDENCY_PROJECT_REQUIRED",
            )
        for project_id in (predecessor.id, successor.id):
            require_project_permission(
                self._user_session,
                project_id,
                "portfolio.manage",
                operation_label="create portfolio dependency",
            )
        self._policy.organization_id(operation_label="create portfolio dependency")
        scope = self._policy.scope(operation_label="create portfolio dependency")
        with self._uow_factory.create(context=new_portfolio_context()) as uow:
            for existing in uow.dependencies.list():
                if (
                    existing.predecessor_project_id == predecessor.id
                    and existing.successor_project_id == successor.id
                ):
                    raise ValidationError(
                        "That portfolio dependency already exists.",
                        code="PORTFOLIO_DEPENDENCY_DUPLICATE",
                    )
            uow.dependencies.add(dependency)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="portfolio_project_dependency",
                entity_id=dependency.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                after_data={
                    "predecessor_project_id": predecessor.id,
                    "successor_project_id": successor.id,
                },
                workspace_id=successor.id,
                metadata={"action": "portfolio.project_dependency.add"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="portfolio.project_dependency.add",
                entity_type="portfolio_project_dependency",
                entity_id=dependency.id,
                module="project_management",
                workspace_id=successor.id,
                details={
                    "predecessor_project_id": predecessor.id,
                    "predecessor_project_name": predecessor.name,
                    "successor_project_id": successor.id,
                    "successor_project_name": successor.name,
                    "dependency_type": dependency.dependency_type.value,
                    "summary": dependency.summary,
                },
                commit=False,
            )
            uow.record_event(
                PortfolioProjectDependencyChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    dependency_id=dependency.id,
                    predecessor_project_id=predecessor.id,
                    successor_project_id=successor.id,
                    change_type=PortfolioProjectDependencyChangeType.ADDED,
                    occurred_at=utc_now(),
                )
            )
            uow.commit()
        return dependency

    def remove_project_dependency(self, dependency_id: str) -> None:
        require_permission(self._user_session, "portfolio.manage", operation_label="remove portfolio dependency")
        self._policy.organization_id(
            operation_label="remove portfolio dependency"
        )
        scope = self._policy.scope(operation_label="remove portfolio dependency")
        dependency = self._dependency_repo.get(dependency_id)
        if dependency is None:
            raise NotFoundError(
                "Portfolio dependency not found.",
                code="PORTFOLIO_DEPENDENCY_NOT_FOUND",
            )
        accessible_projects = {project.id: project for project in self._policy.accessible_projects()}
        predecessor = accessible_projects.get(dependency.predecessor_project_id)
        successor = accessible_projects.get(dependency.successor_project_id)
        if predecessor is None or successor is None:
            raise ValidationError(
                "You no longer have access to one of the projects in this dependency.",
                code="PORTFOLIO_DEPENDENCY_SCOPE_INVALID",
            )
        with self._uow_factory.create(context=new_portfolio_context()) as uow:
            uow.dependencies.delete(dependency_id)
            record_audit_entry(
                uow,
                operation="delete",
                entity_type="portfolio_project_dependency",
                entity_id=dependency.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="low",
                before_data={
                    "predecessor_project_id": predecessor.id,
                    "successor_project_id": successor.id,
                },
                workspace_id=successor.id,
                metadata={"action": "portfolio.project_dependency.remove"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="portfolio.project_dependency.remove",
                entity_type="portfolio_project_dependency",
                entity_id=dependency.id,
                module="project_management",
                workspace_id=successor.id,
                details={
                    "predecessor_project_id": predecessor.id,
                    "predecessor_project_name": predecessor.name,
                    "successor_project_id": successor.id,
                    "successor_project_name": successor.name,
                    "dependency_type": dependency.dependency_type.value,
                    "summary": dependency.summary,
                },
                commit=False,
            )
            uow.record_event(
                PortfolioProjectDependencyChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    dependency_id=dependency.id,
                    predecessor_project_id=predecessor.id,
                    successor_project_id=successor.id,
                    change_type=PortfolioProjectDependencyChangeType.REMOVED,
                    occurred_at=utc_now(),
                )
            )
            uow.commit()


__all__ = ["PortfolioDependencyCommandHandler"]
