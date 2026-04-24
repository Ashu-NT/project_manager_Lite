from __future__ import annotations

from src.api.desktop.platform import ApprovalStatus, PlatformApprovalDesktopApi, PlatformAuditDesktopApi
from src.ui_qml.platform.view_models import (
    PlatformMetricViewModel,
    PlatformWorkspaceOverviewViewModel,
    PlatformWorkspaceRowViewModel,
    PlatformWorkspaceSectionViewModel,
)


class PlatformControlWorkspacePresenter:
    def __init__(
        self,
        *,
        approval_api: PlatformApprovalDesktopApi | None = None,
        audit_api: PlatformAuditDesktopApi | None = None,
    ) -> None:
        self._approval_api = approval_api
        self._audit_api = audit_api

    def build_overview(self) -> PlatformWorkspaceOverviewViewModel:
        approval_rows = self._tuple_data(
            self._approval_api.list_requests(status=None, limit=50) if self._approval_api is not None else None
        )
        audit_rows = self._tuple_data(
            self._audit_api.list_recent(limit=25) if self._audit_api is not None else None
        )

        if self._approval_api is None and self._audit_api is None:
            return PlatformWorkspaceOverviewViewModel(
                title="Control Center",
                subtitle="Control desktop APIs are not connected in this QML preview.",
                status_label="Preview",
                metrics=(
                    PlatformMetricViewModel("Pending approvals", "0", "API not connected"),
                    PlatformMetricViewModel("Audit entries", "0", "API not connected"),
                ),
            )

        pending_count = sum(1 for row in approval_rows if row.status == ApprovalStatus.PENDING)
        approved_count = sum(1 for row in approval_rows if row.status == ApprovalStatus.APPROVED)
        rejected_count = sum(1 for row in approval_rows if row.status == ApprovalStatus.REJECTED)

        return PlatformWorkspaceOverviewViewModel(
            title="Control Center",
            subtitle="Governance queue and audit visibility grouped for the QML control surface.",
            status_label="Connected",
            metrics=(
                PlatformMetricViewModel("Pending approvals", str(pending_count), "Requests awaiting decision"),
                PlatformMetricViewModel("Approved", str(approved_count), "Requests already applied"),
                PlatformMetricViewModel("Rejected", str(rejected_count), "Requests closed without apply"),
                PlatformMetricViewModel("Audit entries", str(len(audit_rows)), "Recent governance and activity trail"),
            ),
            sections=(
                PlatformWorkspaceSectionViewModel(
                    title="Approval Queue Snapshot",
                    rows=tuple(
                        PlatformWorkspaceRowViewModel(
                            row.display_label,
                            row.status.value.title(),
                            row.context_label or row.module_label,
                        )
                        for row in approval_rows[:5]
                    ),
                    empty_state="No approval requests are available yet.",
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Recent Audit Trail",
                    rows=tuple(
                        PlatformWorkspaceRowViewModel(
                            row.action,
                            row.entity_label,
                            row.project_label,
                        )
                        for row in audit_rows[:5]
                    ),
                    empty_state="No audit records are available yet.",
                ),
            ),
        )

    @staticmethod
    def _tuple_data(result: object | None) -> tuple[object, ...]:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return ()
        return tuple(result.data)


__all__ = ["PlatformControlWorkspacePresenter"]
