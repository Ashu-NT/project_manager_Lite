from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.services.collaboration import CollaborationService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


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
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_mark_read = QPushButton("Mark Selected Task Read")
        for button in (self.btn_refresh, self.btn_mark_read):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        badge_row.addWidget(self.unread_label)
        badge_row.addWidget(self.activity_label)
        badge_row.addStretch()
        badge_row.addWidget(self.btn_mark_read)
        badge_row.addWidget(self.btn_refresh)
        root.addLayout(badge_row)

        self.inbox_table = QTableWidget(0, 6)
        self.inbox_table.setHorizontalHeaderLabels(["When", "Project", "Task", "From", "Mentions", "Preview"])
        self.inbox_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.inbox_table.setSelectionMode(QTableWidget.SingleSelection)
        self.inbox_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.inbox_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.inbox_table)
        root.addWidget(QLabel("Mentions"))
        root.addWidget(self.inbox_table, 1)

        self.activity_table = QTableWidget(0, 6)
        self.activity_table.setHorizontalHeaderLabels(["When", "Project", "Task", "From", "Mentions", "Preview"])
        self.activity_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.activity_table.setSelectionMode(QTableWidget.SingleSelection)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.activity_table)
        root.addWidget(QLabel("Recent Activity"))
        root.addWidget(self.activity_table, 1)

        self.btn_refresh.clicked.connect(self.reload_data)
        self.btn_mark_read.clicked.connect(self._mark_selected_task_read)

    def reload_data(self) -> None:
        try:
            inbox = self._collaboration_service.list_inbox(limit=200)
            activity = self._collaboration_service.list_recent_activity(limit=200)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Collaboration", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Collaboration", f"Failed to load collaboration data:\n{exc}")
            return
        self.unread_label.setText(f"Unread mentions: {sum(1 for item in inbox if item.unread)}")
        self.activity_label.setText(f"Recent updates: {len(activity)}")
        self._populate_table(self.inbox_table, inbox)
        self._populate_table(self.activity_table, activity)

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
