from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.core.platform.approval import ApprovalService
from src.core.platform.auth import UserSessionContext
from ui.platform.admin.shared_header import build_admin_header
from src.ui.platform.workspaces.control.approvals.queue import ApprovalQueuePanel
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class ApprovalControlTab(QWidget):
    def __init__(
        self,
        *,
        approval_service: ApprovalService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._approval_service = approval_service
        self._user_session = user_session
        self._can_decide = bool(user_session is not None and user_session.has_permission("approval.decide"))
        self._can_view = bool(
            user_session is not None
            and (
                user_session.has_permission("approval.request")
                or user_session.has_permission("approval.decide")
            )
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        build_admin_header(
            self,
            root,
            object_name="approvalControlHeaderCard",
            eyebrow_text="PLATFORM CONTROL",
            title_text="Approvals",
            subtitle_text="Review governed changes across modules from one shared approval queue.",
            badge_specs=(
                ("approval_scope_badge", "Shared Review", "accent"),
                ("approval_access_badge", self._access_badge_label(), "meta"),
                ("approval_status_badge", "Pending", "meta"),
                ("approval_count_badge", "0 requests", "meta"),
            ),
        )

        self.queue_panel = ApprovalQueuePanel(
            approval_service=self._approval_service,
            user_session=self._user_session,
            summary_changed=self._on_summary_changed,
            parent=self,
        )
        self.table = self.queue_panel.table
        self.status_combo = self.queue_panel.status_combo
        self.btn_refresh = self.queue_panel.btn_refresh
        self.btn_approve = self.queue_panel.btn_approve
        self.btn_reject = self.queue_panel.btn_reject
        root.addWidget(self.queue_panel, 1)

    def _access_badge_label(self) -> str:
        if self._can_decide:
            return "Decision Enabled"
        if self._can_view:
            return "Request Tracking"
        return "Read Only"

    def _on_summary_changed(self, count: int, status_label: str) -> None:
        self.approval_status_badge.setText(status_label)
        self.approval_count_badge.setText(f"{count} requests")


__all__ = ["ApprovalControlTab"]
