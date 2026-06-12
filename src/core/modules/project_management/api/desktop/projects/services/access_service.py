"""Access resolution and permission fallback helpers."""

from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError


def resolve_user_session(project_service=None, project_resource_service=None, resource_service=None):
    """Find the first available user session across injected services."""
    for service in (project_resource_service, resource_service, project_service):
        if service is not None:
            user_session = getattr(service, "_user_session", None)
            if user_session is not None:
                return user_session
    return None


def can_fallback_project_access(
    project_id: str,
    exc: BusinessRuleError,
    *,
    user_session=None,
) -> bool:
    """Return True when a permission-limited user still has sufficient access via a fallback path."""
    message = str(exc)
    if "project.read" not in message and "resource.read" not in message:
        return False
    normalized_id = str(project_id or "").strip()
    if not normalized_id:
        return False
    if user_session is None:
        return False
    if user_session.has_project_permission(normalized_id, "project.manage"):
        return True
    if user_session.has_project_permission(normalized_id, "project.read"):
        return True
    if (
        not user_session.is_project_restricted()
        and (
            user_session.has_permission("project.manage")
            or user_session.has_permission("project.read")
        )
    ):
        return True
    return False


__all__ = ["can_fallback_project_access", "resolve_user_session"]
