from __future__ import annotations

from typing import Any

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.approval import ApprovalRequest, ApprovalStatus
from src.core.shared.audit import record_audit_entry


class _EnterpriseAuditServiceOwner:
    """Minimal duck-type carrier so `record_audit_entry`'s owner-based lookup
    (`getattr(owner, "_enterprise_audit_service", None)`) works here without coupling this
    transaction-agnostic module to any concrete UnitOfWork type -- callers pass the
    `EnterpriseAuditService` instance directly, never an `owner` object of their own."""

    __slots__ = ("_enterprise_audit_service",)

    def __init__(self, enterprise_audit_service: Any) -> None:
        self._enterprise_audit_service = enterprise_audit_service


def build_request_audit_details(
    request: ApprovalRequest,
    *,
    decision_note: str | None = None,
) -> dict[str, str]:
    """Shared with `ApprovalService.reject`/`approve_and_apply`'s own audit metadata --
    the SAME derivation, never duplicated a second time."""
    payload = request.payload or {}
    details: dict[str, str] = {
        "request_type": request.request_type,
        "entity_type": request.entity_type,
    }
    baseline_name = str(payload.get("name") or "").strip()
    project_name = str(payload.get("project_name") or "").strip()
    if baseline_name:
        details["baseline_name"] = baseline_name
    if project_name:
        details["project_name"] = project_name
    cost_desc = str(payload.get("description") or "").strip()
    task_name = str(payload.get("task_name") or "").strip()
    if cost_desc:
        details["cost_description"] = cost_desc
    if task_name:
        details["task_name"] = task_name
    predecessor_name = str(payload.get("predecessor_name") or "").strip()
    successor_name = str(payload.get("successor_name") or "").strip()
    if predecessor_name:
        details["predecessor_name"] = predecessor_name
    if successor_name:
        details["successor_name"] = successor_name
    if decision_note:
        details["decision_note"] = decision_note
    return details


def request_approval_using(
    *,
    approval_repo,
    enterprise_audit_service: Any,
    request_type: str,
    entity_type: str,
    entity_id: str,
    tenant_id: str,
    organization_id: str | None,
    project_id: str | None = None,
    payload: dict[str, Any] | None = None,
    requested_by_user_id: str | None = None,
    requested_by_username: str | None = None,
) -> ApprovalRequest:
    """Stages a new `ApprovalRequest` (duplicate-pending guard, construction, `repo.add()`,
    fail-closed audit entry) inside the caller's OWN already-open transaction. Never commits;
    the caller calls `uow.commit()` (or equivalent) itself, after this returns.

    `tenant_id` is REQUIRED and never derived here -- the caller resolves it once, from its own
    authoritative context, before calling this function (ADR-005 Section 3's rule: never
    re-derive ambient state after construction). `organization_id` is likewise supplied by the
    caller, never read from ambient `TenantContextService` state inside this module.
    """
    if (
        organization_id
        and project_id
        and hasattr(approval_repo, "project_in_different_organization")
        and approval_repo.project_in_different_organization(project_id, organization_id)
    ):
        raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")

    if organization_id and hasattr(approval_repo, "list_by_status_for_organization"):
        existing_pending = approval_repo.list_by_status_for_organization(
            organization_id,
            ApprovalStatus.PENDING,
            limit=1,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    else:
        existing_pending = approval_repo.list_by_status(
            ApprovalStatus.PENDING,
            limit=1,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    if existing_pending:
        raise BusinessRuleError(
            f"A pending approval already exists for this {entity_type.replace('_', ' ')}. "
            f"Request {existing_pending[0].id} is still pending.",
            code="APPROVAL_DUPLICATE_ENTITY",
        )
    request = ApprovalRequest.create(
        request_type=request_type,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        project_id=project_id,
        organization_id=organization_id,
        payload=payload,
        requested_by_user_id=requested_by_user_id,
        requested_by_username=requested_by_username,
    )
    approval_repo.add(request)
    record_audit_entry(
        _EnterpriseAuditServiceOwner(enterprise_audit_service),
        operation="create",
        entity_type="approval_request",
        entity_id=request.id,
        module="platform",
        severity="medium",
        metadata={"action": "governance.request", **build_request_audit_details(request)},
        commit=False,
        fail_closed=True,
    )
    return request


__all__ = ["build_request_audit_details", "request_approval_using"]
