from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.infra.composition.repositories import RepositoryBundle


def wire_tenant_context_service(repo: Any, tenant_context_service: Any) -> Any:
    if hasattr(repo, "_tenant_context_service"):
        repo._tenant_context_service = tenant_context_service
    return repo


def build_enterprise_audit_service(
    session: Session,
    bundle: RepositoryBundle,
    *,
    user_session: Any,
    tenant_context_service: Any,
) -> EnterpriseAuditService:
    
    audit_repo = wire_tenant_context_service(bundle.audit_entry_repo, tenant_context_service)
    return EnterpriseAuditService(
        session=session,
        audit_repo=audit_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )


def build_activity_service(
    session: Session,
    bundle: RepositoryBundle,
    *,
    user_session: Any,
    tenant_context_service: Any,
) -> ActivityService:
    
    activity_repo = wire_tenant_context_service(bundle.activity_repo, tenant_context_service)
    return ActivityService(
        session=session,
        activity_repo=activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )


__all__ = [
    "wire_tenant_context_service",
    "build_enterprise_audit_service",
    "build_activity_service",
]
