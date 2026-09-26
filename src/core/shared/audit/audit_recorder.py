from __future__ import annotations

from typing import Any

from src.core.platform.common.exceptions import BusinessRuleError


def record_audit_entry(
    owner: object,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    module: str,
    category: str = "COMPLIANCE",
    severity: str = "low",
    result: str = "SUCCESS",
    failure_code: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "user",
    actor_username: str | None = None,
    actor_display_name: str | None = None,
    actor_ip: str | None = None,
    actor_user_agent: str | None = None,
    session_id: str | None = None,
    authentication_method: str | None = None,
    impersonated_by_actor_id: str | None = None,
    service_account_id: str | None = None,
    entity_parent_id: str | None = None,
    entity_version: str | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    changed_fields: dict[str, Any] | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    project_id: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    source: str = "DESKTOP_UI",
    permission_used: str | None = None,
    approval_request_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
    fail_closed: bool = False,
) -> None:
    enterprise_audit_service = getattr(owner, "_enterprise_audit_service", None)
    if enterprise_audit_service is None:
        if fail_closed:
            raise BusinessRuleError(
                "Enterprise audit service is required for this operation.",
                code="ENTERPRISE_AUDIT_REQUIRED",
            )
        return
    try:
        enterprise_audit_service.record(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            module=module,
            category=category,
            severity=severity,
            result=result,
            failure_code=failure_code,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_username=actor_username,
            actor_display_name=actor_display_name,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            session_id=session_id,
            authentication_method=authentication_method,
            impersonated_by_actor_id=impersonated_by_actor_id,
            service_account_id=service_account_id,
            entity_parent_id=entity_parent_id,
            entity_version=entity_version,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            request_id=request_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            source=source,
            permission_used=permission_used,
            approval_request_id=approval_request_id,
            reason=reason,
            metadata=metadata,
            commit=commit,
        )
    except Exception:
        if fail_closed:
            raise


__all__ = ["record_audit_entry"]
