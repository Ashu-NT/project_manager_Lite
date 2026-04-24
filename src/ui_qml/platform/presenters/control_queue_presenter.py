from __future__ import annotations

from datetime import datetime

from src.api.desktop.platform import (
    ApprovalDecisionCommand,
    ApprovalStatus,
    DesktopApiError,
    DesktopApiResult,
    PlatformApprovalDesktopApi,
    PlatformAuditDesktopApi,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformControlQueuePresenter:
    def __init__(
        self,
        *,
        approval_api: PlatformApprovalDesktopApi | None = None,
        audit_api: PlatformAuditDesktopApi | None = None,
    ) -> None:
        self._approval_api = approval_api
        self._audit_api = audit_api

    def build_approval_queue(self) -> PlatformWorkspaceActionListViewModel:
        if self._approval_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Approval Queue",
                subtitle="Governed changes appear here once the platform approval API is connected.",
                empty_state="Approval desktop API is not connected in this QML preview.",
            )

        result = self._approval_api.list_requests(status=None, limit=50)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load approval requests."
            return PlatformWorkspaceActionListViewModel(
                title="Approval Queue",
                subtitle=message,
                empty_state=message,
            )

        return PlatformWorkspaceActionListViewModel(
            title="Approval Queue",
            subtitle="Approve or reject governed changes from the QML control workspace.",
            empty_state="No approval requests are available yet.",
            items=tuple(
                PlatformWorkspaceActionItemViewModel(
                    id=row.id,
                    title=row.display_label or row.request_type.replace("_", " ").title(),
                    status_label=row.status.value.title(),
                    subtitle=row.context_label or row.module_label or row.entity_type.replace("_", " ").title(),
                    supporting_text=(
                        f"{row.module_label} | requested by {row.requested_by_username or 'system'}"
                    ).strip(),
                    meta_text=self._format_timestamp(row.requested_at),
                    can_primary_action=row.status == ApprovalStatus.PENDING,
                    can_secondary_action=row.status == ApprovalStatus.PENDING,
                    state={
                        "status": row.status.value,
                    },
                )
                for row in result.data
            ),
        )

    def build_audit_feed(self) -> PlatformWorkspaceActionListViewModel:
        if self._audit_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Recent Audit Feed",
                subtitle="Recent audit records appear here once the platform audit API is connected.",
                empty_state="Audit desktop API is not connected in this QML preview.",
            )

        result = self._audit_api.list_recent(limit=25)
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
                    title=row.action.replace("_", " ").title(),
                    status_label=row.entity_label,
                    subtitle=row.project_label,
                    supporting_text=row.details_label,
                    meta_text=self._format_timestamp(row.occurred_at),
                    state={
                        "entityType": row.entity_type,
                    },
                )
                for row in result.data
            ),
        )

    def approve_request(self, request_id: str) -> DesktopApiResult[object]:
        if self._approval_api is None:
            return self._preview_error("Platform approval API is not connected in this QML preview.")
        return self._approval_api.approve_and_apply(ApprovalDecisionCommand(request_id=request_id))

    def reject_request(self, request_id: str) -> DesktopApiResult[object]:
        if self._approval_api is None:
            return self._preview_error("Platform approval API is not connected in this QML preview.")
        return self._approval_api.reject(ApprovalDecisionCommand(request_id=request_id))

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
