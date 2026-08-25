"""Private helper shared by every `build_<x>_approval_deps(session, ...)` factory in this
package. `build_repository_bundle(session)` constructs each repository fresh but leaves
`_tenant_context_service` unset (`platform_registry.py` wires it separately, once, at process
startup, over the whole `RepositoryBundle`) -- every approval-apply factory needs the identical
wiring step repeated over its own freshly-built repositories.
"""

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
    """Fresh, same-session `EnterpriseAuditService` -- ADR-PF-008 requires the audit row to
    commit atomically with the business mutation, so this (unlike `user_session`/
    `tenant_context_service`) is never reused across a different Session."""
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
    """Fresh, same-session `ActivityService` -- an approval-apply body that records activity
    (e.g. `BaselineService._apply_baseline_creation_decision`) always does so with `commit=False`,
    but the activity row must still be staged on the same Session as the business mutation it
    describes, so (like `EnterpriseAuditService` above) this is never reused across a different
    Session."""
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
