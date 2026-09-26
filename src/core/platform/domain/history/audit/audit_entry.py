from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.core.platform.common.ids import generate_id

# Result outcomes: SUCCESS for a committed operation, DENIED for a policy/
# permission refusal worth recording as its own forensic fact, FAILED for an
# operation that raised before it could complete.
AUDIT_RESULTS = frozenset({"SUCCESS", "DENIED", "FAILED"})

# Classification axis (orthogonal to severity): what KIND of evidence this
# is, not how urgent it is. Kept to the set Platform/PM actually produce --
# extend only when a new kind of evidence is genuinely introduced.
AUDIT_CATEGORIES = frozenset(
    {
        "SECURITY",
        "ACCESS",
        "FINANCIAL",
        "APPROVAL",
        "COMPLIANCE",
        "MASTER_DATA",
        "CONFIGURATION",
        "DATA_EXPORT",
        "DATA_DELETION",
        "INTEGRATION",
        "PRIVILEGED_OPERATION",
    }
)


@dataclass
class AuditEntry:
    """Enterprise compliance/security/financial-governance evidence record.

    Answers "who changed what, when, from where, under what authority, and
    what was the result" for the subset of operations that are materially
    relevant to security, compliance, financial governance, approval/SoD, or
    privileged configuration -- NOT a record of ordinary business activity
    (see src.core.platform.domain.history.activity.ActivityEntry for that).
    """

    id: str
    timestamp: datetime

    # -- actor -----------------------------------------------------------
    actor_id: str | None
    actor_type: str
    actor_username: str | None
    actor_display_name: str | None
    actor_ip: str | None
    actor_user_agent: str | None
    session_id: str | None
    authentication_method: str | None
    impersonated_by_actor_id: str | None
    service_account_id: str | None

    # -- entity / scope ----------------------------------------------------
    entity_type: str
    entity_id: str
    entity_parent_id: str | None
    entity_version: str | None

    module: str
    tenant_id: str | None
    organization_id: str | None
    workspace_id: str | None
    project_id: str | None

    # -- action / classification / outcome --------------------------------
    operation: str
    category: str
    severity: str
    result: str
    failure_code: str | None

    # -- change evidence (controlled snapshots/diffs, never a blind ORM
    # dump) -------------------------------------------------------------
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    changed_fields: dict[str, Any] | None

    # -- request / trace context -------------------------------------------
    request_id: str | None
    correlation_id: str | None
    causation_id: str | None
    source: str

    # -- authority context --------------------------------------------------
    permission_used: str | None
    approval_request_id: str | None
    reason: str | None

    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
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
        tenant_id: str | None = None,
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
    ) -> AuditEntry:
        normalized_category = str(category or "COMPLIANCE").strip().upper()
        if normalized_category not in AUDIT_CATEGORIES:
            normalized_category = "COMPLIANCE"
        normalized_result = str(result or "SUCCESS").strip().upper()
        if normalized_result not in AUDIT_RESULTS:
            normalized_result = "SUCCESS"
        return AuditEntry(
            id=generate_id(),
            timestamp=datetime.now(timezone.utc),
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
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=entity_parent_id,
            entity_version=entity_version,
            module=module,
            tenant_id=tenant_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            operation=operation,
            category=normalized_category,
            severity=severity,
            result=normalized_result,
            failure_code=failure_code,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
            request_id=request_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            source=source,
            permission_used=permission_used,
            approval_request_id=approval_request_id,
            reason=reason,
            metadata=metadata or {},
        )


__all__ = ["AUDIT_CATEGORIES", "AUDIT_RESULTS", "AuditEntry"]
