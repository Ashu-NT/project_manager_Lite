from __future__ import annotations

import logging

from src.api.desktop.platform import PlatformApprovalDesktopApi
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
)

from .formatting import format_timestamp, iso_datetime

logger = logging.getLogger(__name__)


def valid_approval_rows(rows) -> tuple[object, ...]:
    valid: list[object] = []
    for row in rows or ():
        if row is None:
            logger.warning("Skipping null approval row while building collaboration approvals.")
            continue
        request_id = str(getattr(row, "id", "") or "").strip()
        if not request_id:
            logger.warning("Skipping malformed approval row without id: %r", row)
            continue
        valid.append(row)
    return tuple(valid)


def build_approvals_collection(
    approval_api: PlatformApprovalDesktopApi | None,
    *,
    limit: int,
) -> CollaborationCollectionViewModel:
    if approval_api is None:
        return CollaborationCollectionViewModel(
            title="Approvals",
            subtitle="Platform approval API is not connected in this QML preview.",
            empty_state="No approval requests are available yet.",
        )
    result = approval_api.list_requests(status=None, limit=limit)
    if not result.ok or result.data is None:
        message = (
            result.error.message if result.error is not None else "Unable to load approvals."
        )
        return CollaborationCollectionViewModel(
            title="Approvals",
            subtitle=message,
            empty_state=message,
        )
    rows = valid_approval_rows(result.data)
    return CollaborationCollectionViewModel(
        title="Approvals",
        subtitle="Governed workflow approvals linked to project execution and operational delivery.",
        empty_state="No approval requests are available right now.",
        items=tuple(
            CollaborationRecordViewModel(
                id=row.id,
                title=row.display_label or row.request_type.replace("_", " ").title(),
                status_label=row.status.value.title(),
                subtitle=" | ".join(
                    value
                    for value in (row.module_label, row.context_label)
                    if value
                ),
                supporting_text=f"Requested by @{row.requested_by_username or 'system'}",
                meta_text=format_timestamp(row.requested_at),
                can_primary_action=row.status.value.upper() == "PENDING",
                can_secondary_action=row.status.value.upper() == "PENDING",
                state={
                    "panelId": "approvals",
                    "routeId": "platform.control",
                    "projectId": row.project_id or "",
                    "requestId": row.id,
                    "entityId": row.entity_id,
                    "entityType": row.entity_type,
                    "requestType": row.request_type,
                    "moduleLabel": row.module_label,
                    "contextLabel": row.context_label,
                    "requestor": row.requested_by_username or "system",
                    "createdAt": iso_datetime(row.requested_at),
                    "status": row.status.value,
                },
            )
            for row in rows
        ),
    )
