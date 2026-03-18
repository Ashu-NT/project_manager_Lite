from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.modules.project_management.services.collaboration import CollaborationService
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class CollaborationTab(QWidget):
    def __init__(
        self,
        *,
        collaboration_service: CollaborationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._collaboration_service = collaboration_service
        self._setup_ui()
        self.reload_data()
        domain_events.collaboration_changed.connect(self._on_domain_change)
        domain_events.project_changed.connect(self._on_domain_change)
        domain_events.tasks_changed.connect(self._on_domain_change)
        domain_events.approvals_changed.connect(self._on_domain_change)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Collaboration Inbox")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Track mentions and recent task updates across the projects you can access.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        badge_row = QHBoxLayout()
        self.unread_label = QLabel("Unread mentions: 0")
        self.activity_label = QLabel("Recent updates: 0")
        self.notification_label = QLabel("Notifications: 0")
        self.active_label = QLabel("Active now: 0")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        badge_row.addWidget(self.unread_label)
        badge_row.addWidget(self.activity_label)
        badge_row.addWidget(self.notification_label)
        badge_row.addWidget(self.active_label)
        badge_row.addStretch()
        badge_row.addWidget(self.btn_refresh)
        root.addLayout(badge_row)

        self.sections_tabs = QTabWidget()
        self.sections_tabs.setDocumentMode(True)
        root.addWidget(self.sections_tabs, 1)

        self.notifications_table = QTableWidget(0, 5)
        self.notifications_table.setHorizontalHeaderLabels(["When", "Type", "Project", "From", "Summary"])
        self.notifications_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.notifications_table.setSelectionMode(QTableWidget.SingleSelection)
        self.notifications_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.notifications_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.notifications_table)
        notifications_page = QWidget()
        notifications_layout = QVBoxLayout(notifications_page)
        notifications_layout.setContentsMargins(0, 0, 0, 0)
        notifications_layout.setSpacing(CFG.SPACING_SM)
        notifications_hint = QLabel("Workflow notifications for PM activity across projects you can access.")
        notifications_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        notifications_hint.setWordWrap(True)
        notifications_layout.addWidget(notifications_hint)
        notifications_layout.addWidget(self.notifications_table, 1)
        self.sections_tabs.addTab(notifications_page, "Notifications (0)")

        self.inbox_table = QTableWidget(0, 6)
        self.inbox_table.setHorizontalHeaderLabels(["When", "Project", "Task", "From", "Mentions", "Preview"])
        self.inbox_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.inbox_table.setSelectionMode(QTableWidget.SingleSelection)
        self.inbox_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.inbox_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.inbox_table)
        mentions_page = QWidget()
        mentions_layout = QVBoxLayout(mentions_page)
        mentions_layout.setContentsMargins(0, 0, 0, 0)
        mentions_layout.setSpacing(CFG.SPACING_SM)
        mentions_header = QHBoxLayout()
        mentions_hint = QLabel("Mentions needing review. Select a row and mark the task as read when done.")
        mentions_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        mentions_hint.setWordWrap(True)
        self.btn_mark_read = QPushButton("Mark Selected Task Read")
        self.btn_mark_read.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_mark_read.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        mentions_header.addWidget(mentions_hint, 1)
        mentions_header.addWidget(self.btn_mark_read)
        mentions_layout.addLayout(mentions_header)
        mentions_layout.addWidget(self.inbox_table, 1)
        self.sections_tabs.addTab(mentions_page, "Mentions (0)")

        self.activity_table = QTableWidget(0, 6)
        self.activity_table.setHorizontalHeaderLabels(["When", "Project", "Task", "From", "Mentions", "Preview"])
        self.activity_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.activity_table.setSelectionMode(QTableWidget.SingleSelection)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.activity_table)
        activity_page = QWidget()
        activity_layout = QVBoxLayout(activity_page)
        activity_layout.setContentsMargins(0, 0, 0, 0)
        activity_layout.setSpacing(CFG.SPACING_SM)
        activity_hint = QLabel("Recent PM collaboration updates across the accessible project set.")
        activity_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        activity_hint.setWordWrap(True)
        activity_layout.addWidget(activity_hint)
        activity_layout.addWidget(self.activity_table, 1)
        self.sections_tabs.addTab(activity_page, "Recent Activity (0)")

        self.active_table = QTableWidget(0, 5)
        self.active_table.setHorizontalHeaderLabels(["When", "Project", "Task", "Who", "Activity"])
        self.active_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.active_table.setSelectionMode(QTableWidget.SingleSelection)
        self.active_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.active_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.active_table)
        active_page = QWidget()
        active_layout = QVBoxLayout(active_page)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(CFG.SPACING_SM)
        active_hint = QLabel("People currently active in PM task collaboration and edit flows.")
        active_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        active_hint.setWordWrap(True)
        active_layout.addWidget(active_hint)
        active_layout.addWidget(self.active_table, 1)
        self.sections_tabs.addTab(active_page, "Active Now (0)")

        self.btn_refresh.clicked.connect(self.reload_data)
        self.btn_mark_read.clicked.connect(self._mark_selected_task_read)

    def reload_data(self) -> None:
        try:
            snapshot = self._collaboration_service.list_workspace_snapshot(limit=200)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Collaboration", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Collaboration", f"Failed to load collaboration data:\n{exc}")
            return
        self._apply_snapshot(snapshot)

    def _apply_snapshot(self, snapshot) -> None:
        notifications = snapshot.notifications
        inbox = snapshot.inbox
        activity = snapshot.recent_activity
        active_presence = snapshot.active_presence
        self.notification_label.setText(f"Notifications: {len(notifications)}")
        self.unread_label.setText(f"Unread mentions: {sum(1 for item in inbox if item.unread)}")
        self.activity_label.setText(f"Recent updates: {len(activity)}")
        self.active_label.setText(f"Active now: {len(active_presence)}")
        self.sections_tabs.setTabText(0, f"Notifications ({len(notifications)})")
        self.sections_tabs.setTabText(1, f"Mentions ({len(inbox)})")
        self.sections_tabs.setTabText(2, f"Recent Activity ({len(activity)})")
        self.sections_tabs.setTabText(3, f"Active Now ({len(active_presence)})")
        self._populate_notifications_table(notifications)
        self._populate_table(self.inbox_table, inbox)
        self._populate_table(self.activity_table, activity)
        self._populate_active_table(active_presence)

    def _populate_notifications_table(self, rows) -> None:
        self.notifications_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.created_at.strftime("%Y-%m-%d %H:%M"),
                item.notification_type.title(),
                item.project_name or "-",
                item.actor_username,
                f"{item.headline} - {item.body_preview}".strip(" -"),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if item.attention:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                self.notifications_table.setItem(row_idx, col, cell)

    def _populate_table(self, table: QTableWidget, rows) -> None:
        table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            values = [
                item.created_at.strftime("%Y-%m-%d %H:%M"),
                item.project_name,
                item.task_name,
                item.author_username,
                ", ".join(f"@{mention}" for mention in item.mentions) if item.mentions else "-",
                item.body_preview,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 2:
                    cell.setData(Qt.UserRole, item.task_id)
                if table is self.inbox_table and item.unread:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                table.setItem(row_idx, col, cell)

    def _populate_active_table(self, rows) -> None:
        self.active_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            who = item.display_name or f"@{item.username}"
            if item.display_name and item.username:
                who = f"{item.display_name} (@{item.username})"
            values = [
                item.last_seen_at.strftime("%Y-%m-%d %H:%M"),
                item.project_name,
                item.task_name,
                who,
                item.activity.replace("_", " ").title(),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if item.is_self:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                self.active_table.setItem(row_idx, col, cell)

    def _mark_selected_task_read(self) -> None:
        row = self.inbox_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Collaboration", "Select a mention row first.")
            return
        item = self.inbox_table.item(row, 2)
        task_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not task_id:
            return
        try:
            self._collaboration_service.mark_task_mentions_read(task_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Collaboration", str(exc))
            return
        self.reload_data()

    def _on_domain_change(self, _payload: str) -> None:
        self.reload_data()


__all__ = ["CollaborationTab"]
