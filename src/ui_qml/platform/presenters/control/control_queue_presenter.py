from __future__ import annotations

import logging
from datetime import datetime

from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.approval.models.approval import ApprovalDecisionCommand
from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.core.platform.domain.approval import ApprovalStatus
from src.core.platform.api.desktop.history.audit.audit_enterprise import PlatformEnterpriseAuditDesktopApi
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
)

logger = logging.getLogger(__name__)

_APPROVAL_STATUS_TONE: dict[ApprovalStatus, str] = {
    ApprovalStatus.PENDING: "warning",
    ApprovalStatus.APPROVED: "success",
    ApprovalStatus.REJECTED: "danger",
}

_AUDIT_SEVERITY_TONE: dict[str, str] = {
    "critical": "danger",
    "high": "danger",
    "medium": "warning",
    "low": "neutral",
}


class PlatformControlQueuePresenter:
    def __init__(
        self,
        *,
        approval_api: PlatformApprovalDesktopApi | None = None,
        audit_api: PlatformEnterpriseAuditDesktopApi | None = None,
    ) -> None:
        self._approval_api = approval_api
        self._audit_api = audit_api

    def build_approval_queue(
        self,
        *,
        status: str | None = None,
        entity_type: str | None = None,
    ) -> PlatformWorkspaceActionListViewModel:
        rows, error_message = self._fetch_approval_rows(status=status, entity_type=entity_type)
        if error_message is not None:
            return PlatformWorkspaceActionListViewModel(
                title="Approval Queue",
                subtitle=error_message,
                empty_state=error_message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Approval Queue",
            subtitle="Approve or reject governed changes from the QML control workspace.",
            empty_state="No approval requests are available yet.",
            items=tuple(self.serialize_approval_item(row) for row in rows),
        )

    def build_approval_activity_preview(
        self,
        *,
        status: str | None = None,
        entity_type: str | None = None,
        limit: int = 5,
    ) -> tuple[ActivityItemViewModel, ...]:
        """A compact ActivityFeed-shaped preview of the same approval queue
        `build_approval_queue` renders as a full table -- built from the same
        rows, with an explicit tone derived from the real ApprovalStatus
        value rather than any display text."""
        rows, error_message = self._fetch_approval_rows(status=status, entity_type=entity_type)
        if error_message is not None:
            return ()
        return tuple(self._build_approval_activity_item(row) for row in rows[:limit])

    def _fetch_approval_rows(
        self,
        *,
        status: str | None,
        entity_type: str | None,
    ) -> tuple[tuple[object, ...], str | None]:
        if self._approval_api is None:
            return (), "Approval desktop API is not connected in this QML preview."
        result = self._approval_api.list_requests(status=status, entity_type=entity_type, limit=50)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load approval requests."
            return (), message
        return self._valid_approval_rows(result.data), None

    @staticmethod
    def _build_approval_activity_item(row) -> ActivityItemViewModel:
        return ActivityItemViewModel(
            id=row.id,
            title=row.display_label or row.request_type.replace("_", " ").title(),
            actor_display=row.requested_by_username or "System",
            subject_display=row.context_label or row.module_label or "",
            occurred_at=row.requested_at,
            occurred_at_label=PlatformControlQueuePresenter._format_timestamp(row.requested_at),
            icon_key="approve",
            tone=_APPROVAL_STATUS_TONE.get(row.status, "neutral"),
            badge_label=row.status.value.title() if row.status != ApprovalStatus.PENDING else "",
        )

    def build_audit_feed(
        self,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
    ) -> PlatformWorkspaceActionListViewModel:
        if self._audit_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Recent Audit Feed",
                subtitle="Recent audit records appear here once the platform audit API is connected.",
                empty_state="Audit desktop API is not connected in this QML preview.",
            )

        result = self._audit_api.list_recent(
            limit=25, entity_type=entity_type, operation=operation, severity=severity
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load audit records."
            return PlatformWorkspaceActionListViewModel(
                title="Recent Audit Feed",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Recent Audit Feed",
            subtitle="Recent decisions and governance activity stay visible in the QML control surface.",
            empty_state="No audit records are available yet.",
            items=tuple(
                PlatformWorkspaceActionItemViewModel(
                    id=row.id,
                    title=row.operation.replace("_", " ").title(),
                    status_label=row.entity_type.replace("_", " ").title(),
                    subtitle=row.actor_username or "",
                    supporting_text=f"{row.module} | {row.severity}",
                    meta_text=self._format_timestamp(row.timestamp),
                    state={
                        "entityType": row.entity_type,
                    },
                )
                for row in result.data
            ),
        )

    def build_audit_activity_preview(
        self,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
        limit: int = 10,
    ) -> tuple[ActivityItemViewModel, ...]:
        """A compact ActivityFeed-shaped preview of the same audit records
        `build_audit_feed` renders as a full table -- built from the same
        rows, with an explicit tone derived from the real severity value
        rather than any display text."""
        if self._audit_api is None:
            return ()
        result = self._audit_api.list_recent(
            limit=limit, entity_type=entity_type, operation=operation, severity=severity
        )
        if not result.ok or result.data is None:
            return ()
        return tuple(self._build_audit_activity_item(row) for row in result.data)

    @staticmethod
    def _build_audit_activity_item(row) -> ActivityItemViewModel:
        severity = str(row.severity or "").lower()
        return ActivityItemViewModel(
            id=row.id,
            title=humanize_action(row.operation),
            actor_display=row.actor_username or "System",
            subject_display=row.entity_type.replace("_", " ").title(),
            occurred_at=row.timestamp,
            occurred_at_label=PlatformControlQueuePresenter._format_timestamp(row.timestamp),
            icon_key=icon_key_for_entity_type(row.entity_type),
            tone=_AUDIT_SEVERITY_TONE.get(severity, "neutral"),
            badge_label=row.severity.capitalize() if severity in ("critical", "high") else "",
        )

    def approve_request(self, request_id: str, note: str | None = None) -> DesktopApiResult[object]:
        if self._approval_api is None:
            return self._preview_error("Platform approval API is not connected in this QML preview.")
        return self._approval_api.approve_and_apply(
            ApprovalDecisionCommand(request_id=request_id, note=(note or "").strip() or None)
        )

    def reject_request(self, request_id: str, note: str | None = None) -> DesktopApiResult[object]:
        if self._approval_api is None:
            return self._preview_error("Platform approval API is not connected in this QML preview.")
        return self._approval_api.reject(
            ApprovalDecisionCommand(request_id=request_id, note=(note or "").strip() or None)
        )

    def serialize_approval_item(self, row) -> PlatformWorkspaceActionItemViewModel:
        note_text = str(row.decision_note or "").strip()
        meta_parts = [self._format_timestamp(row.requested_at)]
        if note_text:
            meta_parts.append(f"Decision note: {note_text}")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.display_label or row.request_type.replace("_", " ").title(),
            status_label=row.status.value.title(),
            subtitle=row.context_label or row.module_label or row.entity_type.replace("_", " ").title(),
            supporting_text=(
                f"{row.module_label} | requested by {row.requested_by_username or 'system'}"
            ).strip(),
            meta_text=" | ".join(part for part in meta_parts if part),
            can_primary_action=row.status == ApprovalStatus.PENDING,
            can_secondary_action=row.status == ApprovalStatus.PENDING,
            state={
                "status": row.status.value,
                "decisionNote": note_text,
            },
        )

    @staticmethod
    def _valid_approval_rows(rows) -> tuple[object, ...]:
        valid_rows: list[object] = []
        for row in rows or ():
            if row is None:
                logger.warning("Skipping null approval row while building platform approval queue.")
                continue
            request_id = str(getattr(row, "id", "") or "").strip()
            if not request_id:
                logger.warning("Skipping malformed approval row without id: %r", row)
                continue
            valid_rows.append(row)
        return tuple(valid_rows)

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str:
        if value is None:
            return "Timestamp unavailable"
        return value.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _preview_error(message: str) -> DesktopApiResult[object]:
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="preview_only",
                message=message,
                category="preview",
            ),
        )


__all__ = ["PlatformControlQueuePresenter"]
