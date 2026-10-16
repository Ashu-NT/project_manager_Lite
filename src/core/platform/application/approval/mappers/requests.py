from src.core.platform.application.approval.dto.responses.requests import (
    ApprovalRequestResponse,
)
from src.core.platform.domain.approval import ApprovalRequest


def approval_request_response(request: ApprovalRequest, *, can_decide: bool = False) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=request.id,
        request_type=request.request_type,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        project_id=request.project_id,
        payload=dict(request.payload or {}),
        status=request.status,
        requested_by_user_id=request.requested_by_user_id,
        requested_by_username=request.requested_by_username,
        requested_at=request.requested_at,
        decided_by_user_id=request.decided_by_user_id,
        decided_by_username=request.decided_by_username,
        decided_at=request.decided_at,
        decision_note=request.decision_note,
        can_decide=can_decide,
    )
