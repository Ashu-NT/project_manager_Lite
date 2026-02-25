from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from core.exceptions import BusinessRuleError, NotFoundError
from core.interfaces import ApprovalRepository
from core.models import ApprovalRequest, ApprovalStatus
from core.services.auth.authorization import require_permission
from core.services.auth.session import UserSessionContext

ApplyHandler = Callable[[ApprovalRequest], None]


class ApprovalService:
    def __init__(
        self,
        session: Session,
        approval_repo: ApprovalRepository,
        user_session: UserSessionContext | None = None,
    ):
        self._session = session
        self._approval_repo = approval_repo
        self._user_session = user_session
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
        if commit:
            self._session.commit()
        return request

    def list_pending(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self._approval_repo.list_by_status(
            ApprovalStatus.PENDING,
            limit=limit,
            project_id=project_id,
        )

    def list_recent(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self._approval_repo.list_by_status(
            None,
            limit=limit,
            project_id=project_id,
        )

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
        self._session.commit()
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

        principal = self._user_session.principal if self._user_session else None
        request.status = ApprovalStatus.APPROVED
        request.decided_at = datetime.now(timezone.utc)
        request.decided_by_user_id = principal.user_id if principal else None
        request.decided_by_username = principal.username if principal else None
        request.decision_note = (note or "").strip() or None
        self._approval_repo.update(request)
        self._session.commit()
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


__all__ = ["ApprovalService", "ApplyHandler"]
