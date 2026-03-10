from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from infra.collaboration_store import TaskCollaborationStore
from ui.styles.ui_config import UIConfig as CFG


class TaskCollaborationDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        store: TaskCollaborationStore,
        task_id: str,
        task_name: str,
        username: str,
        mention_aliases: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._task_id = task_id
        self._task_name = task_name
        self._username = username
        self._mention_aliases = [
            str(alias).strip().lower()
            for alias in (mention_aliases or [])
            if str(alias).strip()
        ]
        if not self._mention_aliases and self._username:
            self._mention_aliases.append(str(self._username).strip().lower())
        self._pending_attachments: list[str] = []
        self.setWindowTitle(f"Task Collaboration - {task_name}")
        self._setup_ui()
        self.reload_comments(mark_read=True)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_SM)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.resize(780, 560)

        intro = QLabel(
            "Post comments, mention teammates with @username, and attach file paths for context."
        )
        intro.setStyleSheet(CFG.INFO_TEXT_STYLE)
        intro.setWordWrap(True)
        root.addWidget(intro)
        if self._mention_aliases:
            handles = ", ".join(f"@{alias}" for alias in self._mention_aliases[:4])
            self._handles_hint = QLabel(f"Your mention handles: {handles}")
            self._handles_hint.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
            self._handles_hint.setWordWrap(True)
            root.addWidget(self._handles_hint)

        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        root.addWidget(self.activity_list, 1)

        self.attachments_label = QLabel("Attachments: none")
        self.attachments_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        root.addWidget(self.attachments_label)

        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Add activity update... (use @username for mentions)")
        self.comment_input.setMinimumHeight(120)
        root.addWidget(self.comment_input)

        row = QHBoxLayout()
        self.btn_add_attachment = QPushButton("Attach File")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_post = QPushButton("Post Update")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in (self.btn_add_attachment, self.btn_refresh, self.btn_post, self.btn_close):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)

        self.btn_add_attachment.clicked.connect(self._add_attachment)
        self.btn_refresh.clicked.connect(lambda: self.reload_comments(mark_read=True))
        self.btn_post.clicked.connect(self._post_comment)
        self.btn_close.clicked.connect(self.accept)

    def _add_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Attach file", "", "All files (*.*)")
        if not path:
            return
        self._pending_attachments.append(path)
        self._refresh_attachment_label()

    def _refresh_attachment_label(self) -> None:
        if not self._pending_attachments:
            self.attachments_label.setText("Attachments: none")
            return
        names = [Path(path).name for path in self._pending_attachments]
        preview = ", ".join(names[:4]) + ("..." if len(names) > 4 else "")
        self.attachments_label.setText(f"Attachments: {preview}")

    def reload_comments(self, *, mark_read: bool = True) -> None:
        if mark_read:
            for alias in self._mention_aliases:
                self._store.mark_task_mentions_read(task_id=self._task_id, username=alias)
        comments = self._store.list_comments(self._task_id)
        self.activity_list.clear()
        for row in comments:
            author = str(row.get("author") or "unknown")
            created_at = str(row.get("created_at") or "")
            body = str(row.get("body") or "")
            mentions = [str(m) for m in row.get("mentions", [])]
            attachments = [str(a) for a in row.get("attachments", [])]
            lines = [f"{author}  [{created_at}]"]
            lines.append(body)
            if mentions:
                lines.append(f"Mentions: {', '.join('@' + m for m in mentions)}")
            if attachments:
                lines.append("Attachments:")
                lines.extend(f"- {item}" for item in attachments)
            item = QListWidgetItem("\n".join(lines))
            self.activity_list.addItem(item)

    def _post_comment(self) -> None:
        body = self.comment_input.toPlainText().strip()
        if not body:
            QMessageBox.information(self, "Post Update", "Type a comment before posting.")
            return
        try:
            self._store.add_comment(
                task_id=self._task_id,
                author=self._username or "unknown",
                body=body,
                attachments=list(self._pending_attachments),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Post Update", str(exc))
            return
        self.comment_input.clear()
        self._pending_attachments.clear()
        self._refresh_attachment_label()
        # Keep newly posted mentions unread until user explicitly refreshes.
        self.reload_comments(mark_read=False)


__all__ = ["TaskCollaborationDialog"]
