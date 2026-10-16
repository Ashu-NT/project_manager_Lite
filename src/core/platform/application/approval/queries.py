from __future__ import annotations

from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)
from src.core.platform.application.approval.mappers.requests import (
    approval_request_response,
)
from src.core.platform.application.approval.scope import ApprovalScope
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)
from src.core.platform.domain.approval import ApprovalRequest, ApprovalStatus
from src.core.platform.domain.security.auth.session import UserSessionContext


class ApprovalQueryHandler:
    """Organization-scoped approval queue reads without mutation transactions."""

    def __init__(self, *, approval_repo: ApprovalRepository, scope: ApprovalScope, user_session: UserSessionContext | None = None) -> None:
        self._approval_repo = approval_repo
        self._scope = scope
        self._user_session = user_session

    def list_requests(
        self,
        *,
        status: ApprovalStatus | str | None = None,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        limit: int = 200,
    ) -> list[ApprovalRequestResponse]:
        requests = self._list_request_models(
            status=status, project_id=project_id, entity_type=entity_type, limit=limit,
        )
        eligible_ids = self.eligible_request_ids(tuple(requests))
        return [
            approval_request_response(request, can_decide=request.id in eligible_ids)
            for request in requests
        ]

    def _list_request_models(
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

    def eligible_request_ids(self, requests: tuple[ApprovalRequest, ...]) -> frozenset[str]:
        principal = self._user_session.principal if self._user_session else None
        if principal is None or not requests:
            return frozenset()
        return self._approval_repo.eligible_request_ids(
            tuple(request.id for request in requests), principal.user_id,
        )

    def list_pending(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self._list_request_models(status=ApprovalStatus.PENDING, limit=limit, project_id=project_id)

    def count_pending(self, *, project_id: str | None = None) -> int:
        """Exact count, independent of any list/preview limit -- callers
        that only need "how many" must use this instead of `len()` on a
        possibly-truncated `list_requests`/`list_pending` result."""
        require_any_permission(
            self._user_session,
            ("approval.request", "approval.decide"),
            operation_label="view governance requests",
        )
        return self._count_approval_rows(
            status=ApprovalStatus.PENDING,
            project_id=project_id,
            entity_type=None,
            entity_id=None,
        )

    def list_recent(self, *, project_id: str | None = None, limit: int = 200) -> list[ApprovalRequest]:
        return self._list_request_models(status=None, limit=limit, project_id=project_id)

    def _list_approval_rows(
        self,
        *,
        status: ApprovalStatus | None,
        limit: int,
        project_id: str | None,
        entity_type: str | list[str] | None,
        entity_id: str | None,
    ) -> list[ApprovalRequest]:
        organization_id = self._scope.active_organization_id(operation_label="view governance requests")
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

    def _count_approval_rows(
        self,
        *,
        status: ApprovalStatus | None,
        project_id: str | None,
        entity_type: str | list[str] | None,
        entity_id: str | None,
    ) -> int:
        organization_id = self._scope.active_organization_id(operation_label="view governance requests")
        if organization_id and hasattr(self._approval_repo, "count_by_status_for_organization"):
            return self._approval_repo.count_by_status_for_organization(
                organization_id,
                status,
                project_id=project_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        return self._approval_repo.count_by_status(
            status,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
