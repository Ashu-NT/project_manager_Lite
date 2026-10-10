from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_CHOICES,
    normalize_project_scope_role,
    resolve_project_scope_permissions,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
)
from src.core.platform.access import ScopedRolePolicy


def register_project_scope_access(repositories, platform_services) -> None:
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="project",
            role_choices=PROJECT_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_project_scope_role,
            resolve_permissions=resolve_project_scope_permissions,
        )
    )

    def _project_belongs_to_tenant(tenant_id: str, project_id: str) -> bool:
        # The ambient organization may differ from the project's organization.
        return repositories.pm.project_repo.get_for_tenant(project_id, tenant_id) is not None

    platform_services.access_service.register_scope_exists_resolver(
        "project", _project_belongs_to_tenant
    )
    platform_services.auth_service.register_canonical_scope_tenant_resolver(
        "project", _project_belongs_to_tenant
    )

    def _project_exists_for_role_governance(
        scope_session: Session, tenant_id: str, project_id: str
    ) -> bool:
        return SqlAlchemyProjectRepository(scope_session).get_for_tenant(project_id, tenant_id) is not None

    def _project_organization_owner(
        scope_session: Session, tenant_id: str, project_id: str
    ) -> str | None:
        project = SqlAlchemyProjectRepository(scope_session).get_for_tenant(project_id, tenant_id)
        return getattr(project, "organization_id", None)

    platform_services.role_governance_service.register_scope_exists_resolver(
        "project", _project_exists_for_role_governance
    )
    platform_services.role_governance_service.register_organization_owner_resolver(
        "project", _project_organization_owner
    )
