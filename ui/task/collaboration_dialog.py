from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.models import CollaborationMentionCandidate, TaskComment
from core.services.collaboration import CollaborationService
from infra.collaboration_store import TaskCollaborationStore
from ui.styles.ui_config import UIConfig as CFG
from ui.task.mention_text_edit import TaskMentionTextEdit


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
        collaboration_service: CollaborationService | None = None,
        can_post: bool = True,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._collaboration_service = collaboration_service
        self._task_id = task_id
        self._task_name = task_name
        self._username = username
        self._mention_aliases = [
            str(alias).strip().lower()
            for alias in (mention_aliases or [])
            if str(alias).strip()
        ]
        self._can_post = bool(can_post)
        if not self._mention_aliases and self._username:
            self._mention_aliases.append(str(self._username).strip().lower())
        self._mention_candidates: list[CollaborationMentionCandidate] = []
        self._mention_candidate_error: str = ""
        if self._collaboration_service is not None:
            try:
                self._mention_candidates = self._collaboration_service.list_mention_candidates(task_id)
            except Exception as exc:
                self._mention_candidate_error = str(exc)
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
            "Post comments, mention teammates with @username, and attach files for shared context."
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
        if self._mention_candidates:
            mention_row = QHBoxLayout()
            mention_row.addWidget(QLabel("Mention collaborator:"))
            self.mention_combo = QComboBox()
            self.mention_combo.setEditable(True)
            self.mention_combo.setInsertPolicy(QComboBox.NoInsert)
            self.mention_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)
            self.mention_combo.addItem("Select handle to insert", userData="")
            for candidate in self._mention_candidates:
                self.mention_combo.addItem(candidate.label, userData=candidate.handle)
            self.btn_insert_mention = QPushButton("Insert Mention")
            for widget in (self.mention_combo, self.btn_insert_mention):
                if hasattr(widget, "setFixedHeight"):
                    widget.setFixedHeight(CFG.INPUT_HEIGHT if widget is self.mention_combo else CFG.BUTTON_HEIGHT)
            self.btn_insert_mention.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            self.btn_insert_mention.clicked.connect(self._insert_selected_mention)
            mention_row.addWidget(self.mention_combo, 1)
            mention_row.addWidget(self.btn_insert_mention)
            root.addLayout(mention_row)
        elif self._mention_candidate_error:
            warning = QLabel(f"Mention directory unavailable: {self._mention_candidate_error}")
            warning.setStyleSheet(CFG.NOTE_STYLE_SHEET)
            warning.setWordWrap(True)
            root.addWidget(warning)
        if not self._can_post:
            read_only = QLabel("Read-only access. You can review activity, but posting is disabled.")
            read_only.setStyleSheet(CFG.NOTE_STYLE_SHEET)
            read_only.setWordWrap(True)
            root.addWidget(read_only)

        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        root.addWidget(self.activity_list, 1)

        self.attachments_label = QLabel("Attachments: none")
        self.attachments_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        root.addWidget(self.attachments_label)

        self.comment_input = TaskMentionTextEdit()
        self.comment_input.set_mention_handles([candidate.handle for candidate in self._mention_candidates])
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
        self.btn_add_attachment.setEnabled(self._can_post)
        self.comment_input.setReadOnly(not self._can_post)
        self.btn_post.setEnabled(self._can_post)
        if hasattr(self, "btn_insert_mention"):
            self.btn_insert_mention.setEnabled(self._can_post)

    def _insert_selected_mention(self) -> None:
        handle = str(getattr(self, "mention_combo", None).currentData() or "").strip()
        if not handle:
            return
        cursor = self.comment_input.textCursor()
        before = cursor.block().text()[: cursor.positionInBlock()]
        prefix = "" if not before or before.endswith((" ", "(", "\t")) else " "
        cursor.insertText(f"{prefix}@{handle} ")
        self.comment_input.setFocus()

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
        if self._collaboration_service is not None:
            if mark_read:
                self._collaboration_service.mark_task_mentions_read(self._task_id)
            comments = self._comment_rows_from_service(self._collaboration_service.list_comments(self._task_id))
        else:
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

    @staticmethod
    def _comment_rows_from_service(comments: list[TaskComment]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for comment in comments:
            rows.append(
                {
                    "author": comment.author_username or "unknown",
                    "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M"),
                    "body": comment.body,
                    "mentions": list(comment.mentions or []),
                    "attachments": list(comment.attachments or []),
                }
            )
        return rows

    def _post_comment(self) -> None:
        if not self._can_post:
            QMessageBox.information(self, "Post Update", "Posting is not available in read-only mode.")
            return
        body = self.comment_input.toPlainText().strip()
        if not body:
            QMessageBox.information(self, "Post Update", "Type a comment before posting.")
            return
        try:
            if self._collaboration_service is not None:
                self._collaboration_service.post_comment(
                    task_id=self._task_id,
                    body=body,
                    attachments=list(self._pending_attachments),
                )
            else:
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
