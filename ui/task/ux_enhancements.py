from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut

from ui.styles.ui_config import UIConfig as CFG
from ui.task.collaboration_dialog import TaskCollaborationDialog


class TaskUxEnhancementsMixin:
    def _sync_undo_redo_state(self) -> None:
        self.btn_undo.setEnabled(self._undo_stack.can_undo())
        self.btn_redo.setEnabled(self._undo_stack.can_redo())
        undo_label = self._undo_stack.next_undo_label()
        redo_label = self._undo_stack.next_redo_label()
        self.btn_undo.setText(f"Undo ({undo_label})" if undo_label else "Undo")
        self.btn_redo.setText(f"Redo ({redo_label})" if redo_label else "Redo")

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=lambda: self.btn_new.click())
        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: self.btn_edit.click())
        QShortcut(QKeySequence("Delete"), self, activated=lambda: self.btn_delete.click())
        QShortcut(QKeySequence("Ctrl+Shift+Delete"), self, activated=lambda: self.btn_bulk_delete.click())
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=lambda: self.btn_bulk_status.click())
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo_last_task_action)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo_last_task_action)

    def _apply_accessibility_labels(self) -> None:
        self.btn_new.setToolTip("Ctrl+N")
        self.btn_edit.setToolTip("Ctrl+E")
        self.btn_delete.setToolTip("Delete")
        self.btn_bulk_delete.setToolTip("Ctrl+Shift+Delete")
        self.btn_bulk_status.setToolTip("Ctrl+Shift+S")
        self.btn_undo.setToolTip("Ctrl+Z")
        self.btn_redo.setToolTip("Ctrl+Y")
        self.btn_comments.setToolTip("Open task comments and activity")
        self.btn_new.setAccessibleName("Create New Task")
        self.btn_edit.setAccessibleName("Edit Selected Task")
        self.btn_delete.setAccessibleName("Delete Selected Task")
        self.btn_bulk_status.setAccessibleName("Apply Bulk Task Status")
        self.btn_bulk_delete.setAccessibleName("Delete Multiple Tasks")
        self.btn_comments.setAccessibleName("Open Task Collaboration")
        self.task_search_filter.setAccessibleName("Task Search Filter")
        self.task_status_filter.setAccessibleName("Task Status Filter")
        self.task_priority_filter.setAccessibleName("Task Priority Filter")
        self.task_schedule_filter.setAccessibleName("Task Schedule Filter")

    def _current_username(self) -> str:
        principal = getattr(self._user_session, "principal", None)
        username = getattr(principal, "username", "") if principal is not None else ""
        return str(username or "").strip() or "unknown"

    def _refresh_mentions_badge(self) -> None:
        username = self._current_username()
        unread = self._collaboration_store.unread_mentions_count(username)
        self.lbl_mentions.setText(f"Mentions: {unread}")
        self.lbl_mentions.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)

    def _open_task_collaboration(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        dialog = TaskCollaborationDialog(
            self,
            store=self._collaboration_store,
            task_id=task.id,
            task_name=task.name,
            username=self._current_username(),
        )
        dialog.exec()
        self._refresh_mentions_badge()


__all__ = ["TaskUxEnhancementsMixin"]

