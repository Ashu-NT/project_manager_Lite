from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.repositories import (
    build_project_management_repositories,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    build_platform_repositories,
)


def build_approval_repository_context(
    session: Session, tenant_context_service: Any
) -> ProjectManagementRepositoryContext:
    context = ProjectManagementRepositoryContext(
        pm=build_project_management_repositories(session),
        platform=build_platform_repositories(session),
    )
    for owner in (context.pm, context.platform):
        for field_name in owner.__dataclass_fields__:
            wire_tenant_context_service(getattr(owner, field_name), tenant_context_service)
    return context


def wire_tenant_context_service(repo: Any, tenant_context_service: Any) -> Any:
    if hasattr(repo, "_tenant_context_service"):
        repo._tenant_context_service = tenant_context_service
    return repo


def build_enterprise_audit_service(
    session: Session,
    bundle: ProjectManagementRepositoryContext,
    *,
    user_session: Any,
    tenant_context_service: Any,
) -> EnterpriseAuditService:
    
    audit_repo = wire_tenant_context_service(bundle.platform.audit_entry_repo, tenant_context_service)
    return EnterpriseAuditService(
        session=session,
        audit_repo=audit_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )


def build_activity_service(
    session: Session,
    bundle: ProjectManagementRepositoryContext,
    *,
    user_session: Any,
    tenant_context_service: Any,
) -> ActivityService:
    
    activity_repo = wire_tenant_context_service(bundle.platform.activity_repo, tenant_context_service)
    return ActivityService(
        session=session,
        activity_repo=activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )


__all__ = [
    "build_activity_service",
    "build_approval_repository_context",
    "build_enterprise_audit_service",
    "wire_tenant_context_service",
]
