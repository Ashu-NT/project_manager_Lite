from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, NotFoundError
from core.interfaces import ApprovalRepository
from core.models import ApprovalRequest, ApprovalStatus
from core.services.auth.authorization import require_permission
from core.services.auth.session import UserSessionContext
from core.services.audit.service import AuditService

ApplyHandler = Callable[[ApprovalRequest], None]


class ApprovalService:
    def __init__(
        self,
        session: Session,
        approval_repo: ApprovalRepository,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
    ):
        self._session = session
        self._approval_repo = approval_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._apply_handlers: dict[str, ApplyHandler] = {}

    def register_apply_handler(self, request_type: str, handler: ApplyHandler) -> None:
        self._apply_handlers[request_type.strip().lower()] = handler

    def request_change(
        self,
        *,
        request_type: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> ApprovalRequest:
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="request governed change",
        )
        principal = self._user_session.principal if self._user_session else None
        request = ApprovalRequest.create(
            request_type=request_type.strip().lower(),
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            payload=payload or {},
            requested_by_user_id=principal.user_id if principal else None,
            requested_by_username=principal.username if principal else None,
        )
        self._approval_repo.add(request)
        self._record_governance_audit(
            action="governance.request",
            request=request,
            details={
                "request_type": request.request_type,
                "entity_type": request.entity_type,
                "entity_id": request.entity_id,
            },
        )
        if commit:
            self._session.commit()
            domain_events.approvals_changed.emit(request.id)
        return request

    def list_requests(
        self,
        *,
        status: ApprovalStatus | str | None = None,
        project_id: str | None = None,
        limit: int = 200,
    ) -> list[ApprovalRequest]:
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
        return self._approval_repo.list_by_status(
            normalized_status,
            limit=limit,
            project_id=project_id,
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
        request.decision_note = (note or "").strip() or None
        self._approval_repo.update(request)
        self._record_governance_audit(
            action="governance.reject",
            request=request,
            details={
                "request_type": request.request_type,
                "entity_type": request.entity_type,
                "entity_id": request.entity_id,
                "decision_note": request.decision_note,
            },
        )
        self._session.commit()
        domain_events.approvals_changed.emit(request.id)
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

        handler(request)
        self._emit_post_apply_domain_events(request)

        principal = self._user_session.principal if self._user_session else None
        request.status = ApprovalStatus.APPROVED
        request.decided_at = datetime.now(timezone.utc)
        request.decided_by_user_id = principal.user_id if principal else None
        request.decided_by_username = principal.username if principal else None
        request.decision_note = (note or "").strip() or None
        self._approval_repo.update(request)
        self._record_governance_audit(
            action="governance.approve",
            request=request,
            details={
                "request_type": request.request_type,
                "entity_type": request.entity_type,
                "entity_id": request.entity_id,
                "decision_note": request.decision_note,
            },
        )
        self._session.commit()
        domain_events.approvals_changed.emit(request.id)
        return request

    def _require_pending(self, request_id: str) -> ApprovalRequest:
        request = self._approval_repo.get(request_id)
        if request is None:
            raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")
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
    def _emit_post_apply_domain_events(request: ApprovalRequest) -> None:
        if request.request_type == "baseline.create" and request.project_id:
            domain_events.baseline_changed.emit(request.project_id)

    def _record_governance_audit(
        self,
        *,
        action: str,
        request: ApprovalRequest,
        details: dict | None = None,
    ) -> None:
        if self._audit_service is None:
            return
        self._audit_service.record(
            action=action,
            entity_type="approval_request",
            entity_id=request.id,
            project_id=request.project_id,
            details=details or {},
            commit=False,
        )


__all__ = ["ApprovalService", "ApplyHandler"]
