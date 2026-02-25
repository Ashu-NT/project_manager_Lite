from __future__ import annotations

import json
from typing import Any

from core.models import ApprovalRequest, ApprovalStatus
from infra.db.models import ApprovalRequestORM


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def _from_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def approval_to_orm(request: ApprovalRequest) -> ApprovalRequestORM:
    return ApprovalRequestORM(
        id=request.id,
        request_type=request.request_type,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        project_id=request.project_id,
        payload_json=_to_json(request.payload),
        status=request.status.value,
        requested_by_user_id=request.requested_by_user_id,
        requested_by_username=request.requested_by_username,
        requested_at=request.requested_at,
        decided_by_user_id=request.decided_by_user_id,
        decided_by_username=request.decided_by_username,
        decided_at=request.decided_at,
        decision_note=request.decision_note,
    )


def approval_from_orm(obj: ApprovalRequestORM) -> ApprovalRequest:
    return ApprovalRequest(
        id=obj.id,
        request_type=obj.request_type,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        project_id=obj.project_id,
        payload=_from_json(obj.payload_json),
        status=ApprovalStatus(obj.status),
        requested_by_user_id=obj.requested_by_user_id,
        requested_by_username=obj.requested_by_username,
        requested_at=obj.requested_at,
        decided_by_user_id=obj.decided_by_user_id,
        decided_by_username=obj.decided_by_username,
        decided_at=obj.decided_at,
        decision_note=obj.decision_note,
    )


__all__ = ["approval_to_orm", "approval_from_orm"]

