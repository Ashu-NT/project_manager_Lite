from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.shared.events.domain_events import domain_events
from src.core.shared.audit import record_audit_entry
from src.core.platform.contract.approval.contracts import ApprovalHandlerResult, ApprovalRepository
from src.core.platform.domain.approval import ApprovalRequest, ApprovalStatus
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_any_permission, require_permission
from src.core.platform.domain.security.authorization.roles.role_binding import ROLE_PRINCIPAL_USER
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.shared.notifications import safe_dispatch_notification

logger = logging.getLogger(__name__)

ApplyHandler = Callable[[ApprovalRequest], ApprovalHandlerResult | None]


class ApprovalService:
    def __init__(
        self,
        session: Session,
        approval_repo: ApprovalRepository,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: Any = None,
        tenant_context_service: TenantContextService | None = None,
        notification_service: Any = None,
        role_repo: Any = None,
        role_permission_repo: Any = None,
        permission_repo: Any = None,
        role_binding_repo: Any = None,
    ):
        self._session = session
        self._approval_repo = approval_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._notification_service = notification_service
        self._role_repo = role_repo
        self._role_permission_repo = role_permission_repo
        self._permission_repo = permission_repo
        self._role_binding_repo = role_binding_repo
        self._apply_handlers: dict[str, ApplyHandler] = {}
        self._reject_handlers: dict[str, ApplyHandler] = {}

    def register_apply_handler(self, request_type: str, handler: ApplyHandler) -> None:
        self._apply_handlers[request_type.strip().lower()] = handler

    def register_reject_handler(self, request_type: str, handler: ApplyHandler) -> None:
        self._reject_handlers[request_type.strip().lower()] = handler

    def request_change(
        self,
        *,
        request_type: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        module: str | None = None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> ApprovalRequest:
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="request governed change",
        )
        organization_id = self._active_organization_id(
            operation_label="request governed change"
        )
        self._assert_project_in_active_organization(project_id, operation_label="request governed change")
        existing_pending = self._list_approval_rows(
            status=ApprovalStatus.PENDING,
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
        principal = self._user_session.principal if self._user_session else None
        request = ApprovalRequest.create(
            request_type=request_type,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            organization_id=organization_id,
            payload=payload,
            requested_by_user_id=principal.user_id if principal else None,
            requested_by_username=principal.username if principal else None,
        )
        try:
            self._approval_repo.add(request)
            record_audit_entry(
                self,
                operation="create",
                entity_type="approval_request",
                entity_id=request.id,
                module="platform",
                severity="medium",
                metadata={"action": "governance.request", **self._build_request_audit_details(request)},
                commit=False,
                fail_closed=True,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception:
            if commit:
                self._session.rollback()
            raise
        if commit:
            self._emit_signal_safely("approvals_changed", request.id)
            self._notify_approval_requested(request)
        return request

    def list_requests(
        self,
        *,
        status: ApprovalStatus | str | None = None,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        limit: int = 200,
    ) -> list[ApprovalRequest]:
        require_any_permission(
            self._user_session,
            ("approval.request", "approval.decide"),
            operation_label="view governance requests",
        )
        normalized_status: ApprovalStatus | None
        if isinstance(status, ApprovalStatus) or status is None:
            normalized_status = status
        else:
            raw = str(status).strip()
            if "." in raw:
                raw = raw.rsplit(".", 1)[-1]
            raw = raw.upper()
            try:
                normalized_status = ApprovalStatus(raw)
            except ValueError:
                normalized_status = None
        return self._list_approval_rows(
            status=normalized_status,
            limit=limit,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=None,
        )

    def list_pending(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self.list_requests(status=ApprovalStatus.PENDING, limit=limit, project_id=project_id)

    def list_recent(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self.list_requests(status=None, limit=limit, project_id=project_id)

    def reject(self, request_id: str, note: str | None = None) -> ApprovalRequest:
        require_permission(
            self._user_session,
            "approval.decide",
            operation_label="reject approval request",
        )
        request = self._require_pending(request_id)
        self._ensure_not_self_decision(request)
        principal = self._user_session.principal if self._user_session else None
        request.status = ApprovalStatus.REJECTED
        request.decided_at = datetime.now(timezone.utc)
        request.decided_by_user_id = principal.user_id if principal else None
        request.decided_by_username = principal.username if principal else None
        request.decision_note = note
        handler_result = ApprovalHandlerResult()
        try:
            reject_handler = self._reject_handlers.get(request.request_type)
            if reject_handler is not None:
                handler_result = self._normalize_handler_result(reject_handler(request))
            self._approval_repo.update(request)
            record_audit_entry(
                self,
                operation="update",
                entity_type="approval_request",
                entity_id=request.id,
                module="platform",
                severity="high",
                metadata={"action": "governance.reject", **self._build_request_audit_details(request, decision_note=request.decision_note)},
                commit=False,
                fail_closed=True,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._emit_handler_events(handler_result)
        self._emit_signal_safely("approvals_changed", request.id)
        self._notify_approval_decided(request, decided="rejected")
        return request

    def approve_and_apply(self, request_id: str, note: str | None = None) -> ApprovalRequest:
        require_permission(
            self._user_session,
            "approval.decide",
            operation_label="approve approval request",
        )
        request = self._require_pending(request_id)
        self._ensure_not_self_decision(request)
        handler = self._apply_handlers.get(request.request_type)
        if handler is None:
            raise BusinessRuleError(
                f"No apply handler registered for '{request.request_type}'.",
                code="APPROVAL_HANDLER_MISSING",
            )

        try:
            handler_result = self._normalize_handler_result(handler(request))
            principal = self._user_session.principal if self._user_session else None
            request.status = ApprovalStatus.APPROVED
            request.decided_at = datetime.now(timezone.utc)
            request.decided_by_user_id = principal.user_id if principal else None
            request.decided_by_username = principal.username if principal else None
            request.decision_note = note
            self._approval_repo.update(request)
            record_audit_entry(
                self,
                operation="update",
                entity_type="approval_request",
                entity_id=request.id,
                module="platform",
                severity="high",
                metadata={"action": "governance.approve", **self._build_request_audit_details(request, decision_note=request.decision_note)},
                commit=False,
                fail_closed=True,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._emit_handler_events(handler_result)
        self._emit_signal_safely("approvals_changed", request.id)
        self._notify_approval_decided(request, decided="approved")
        return request

    def _require_pending(self, request_id: str) -> ApprovalRequest:
        request = self._approval_repo.get(request_id)
        if request is None:
            raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")
        self._assert_project_in_active_organization(
            request.project_id,
            operation_label="view approval request",
        )
        if request.status != ApprovalStatus.PENDING:
            raise BusinessRuleError(
                "Approval request is already decided.",
                code="APPROVAL_ALREADY_DECIDED",
            )
        return request

    def _ensure_not_self_decision(self, request: ApprovalRequest) -> None:
        principal = self._user_session.principal if self._user_session else None
        if principal is None or not request.requested_by_user_id:
            return
        if principal.user_id == request.requested_by_user_id:
            raise BusinessRuleError(
                "You cannot approve or reject your own governance request.",
                code="APPROVAL_SELF_DECISION_FORBIDDEN",
            )

    @staticmethod
    def _normalize_handler_result(
        result: ApprovalHandlerResult | None,
    ) -> ApprovalHandlerResult:
        if result is None:
            return ApprovalHandlerResult()
        if not isinstance(result, ApprovalHandlerResult):
            raise BusinessRuleError(
                "Approval apply handler returned an unsupported result.",
                code="APPROVAL_HANDLER_RESULT_INVALID",
            )
        return result

    @classmethod
    def _emit_handler_events(cls, result: ApprovalHandlerResult) -> None:
        for event in result.post_commit_events:
            cls._emit_signal_safely(event.signal_name, event.payload)

    @staticmethod
    def _emit_signal_safely(signal_name: str, payload: str) -> None:
        signal = getattr(domain_events, signal_name, None)
        if signal is None:
            logger.error("Approval post-commit signal is not registered: %s", signal_name)
            return
        try:
            signal.emit(payload)
        except Exception:
            logger.exception(
                "Approval post-commit signal failed signal=%s payload=%s",
                signal_name,
                payload,
            )

    def _active_tenant_id(self) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            return None
        return tenant_context.get_active_tenant_id()

    def _list_users_with_permission(self, permission_code: str, *, tenant_id: str | None) -> set[str]:
        if (
            self._permission_repo is None
            or self._role_repo is None
            or self._role_permission_repo is None
            or self._role_binding_repo is None
        ):
            return set()
        permission = self._permission_repo.get_by_code(permission_code)
        if permission is None:
            return set()
        user_ids: set[str] = set()
        for role in self._role_repo.list_all():
            if permission.id not in self._role_permission_repo.list_permission_ids(role.id):
                continue
            bindings = list(self._role_binding_repo.list_active_for_role_across_tenants(role.id))
            if tenant_id:
                bindings.extend(self._role_binding_repo.list_active_for_role(role.id, tenant_id=tenant_id))
            for binding in bindings:
                if binding.principal_type == ROLE_PRINCIPAL_USER:
                    user_ids.add(binding.principal_id)
        return user_ids

    def _notify_approval_requested(self, request: ApprovalRequest) -> None:
        tenant_id = self._active_tenant_id()
        recipients = self._list_users_with_permission("approval.decide", tenant_id=tenant_id)
        recipients.discard(request.requested_by_user_id)
        entity_label = request.entity_type.replace("_", " ")
        for user_id in recipients:
            safe_dispatch_notification(
                self,
                recipient_user_id=user_id,
                category="approval.requested.v1",
                title="Approval requested",
                body=f"{request.requested_by_username or 'Someone'} requested approval for a {entity_label}.",
                tenant_id=tenant_id,
                metadata={
                    "request_id": request.id,
                    "request_type": request.request_type,
                    "entity_type": request.entity_type,
                    "entity_id": request.entity_id,
                },
            )

    def _notify_approval_decided(self, request: ApprovalRequest, *, decided: str) -> None:
        if not request.requested_by_user_id:
            return
        entity_label = request.entity_type.replace("_", " ")
        body = f"Your {entity_label} request was {decided}."
        if request.decision_note:
            body = f"{body} Note: {request.decision_note}"
        safe_dispatch_notification(
            self,
            recipient_user_id=request.requested_by_user_id,
            category=f"approval.{decided}.v1",
            title=f"Your approval request was {decided}",
            body=body,
            tenant_id=self._active_tenant_id(),
            metadata={"request_id": request.id, "request_type": request.request_type},
        )

    @staticmethod
    def _build_request_audit_details(
        request: ApprovalRequest,
        *,
        decision_note: str | None = None,
    ) -> dict[str, str]:
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

    def _active_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            return None
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _list_approval_rows(
        self,
        *,
        status: ApprovalStatus | None,
        limit: int,
        project_id: str | None,
        entity_type: str | list[str] | None,
        entity_id: str | None,
    ) -> list[ApprovalRequest]:
        organization_id = self._active_organization_id(operation_label="view governance requests")
        if organization_id and hasattr(self._approval_repo, "list_by_status_for_organization"):
            return self._approval_repo.list_by_status_for_organization(
                organization_id,
                status,
                limit=limit,
                project_id=project_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        return self._approval_repo.list_by_status(
            status,
            limit=limit,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def _assert_project_in_active_organization(
        self,
        project_id: str | None,
        *,
        operation_label: str,
    ) -> None:
        organization_id = self._active_organization_id(operation_label=operation_label)
        if not organization_id or not project_id:
            return
        if hasattr(self._approval_repo, "project_in_different_organization") and self._approval_repo.project_in_different_organization(project_id, organization_id):
            raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")


__all__ = ["ApplyHandler", "ApprovalService"]
