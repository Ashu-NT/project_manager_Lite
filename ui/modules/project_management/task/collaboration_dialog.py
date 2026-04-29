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

from core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskComment,
)
from src.core.modules.project_management.application.tasks import CollaborationService
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from ui.modules.project_management.task.document_link_dialogs import ProjectManagementDocumentLinkDialog
from ui.modules.project_management.task.document_labels import format_linked_document_label
from ui.modules.project_management.task.presence import format_presence_lines
from src.ui.shared.formatting.ui_config import UIConfig as CFG
from ui.modules.project_management.task.mention_text_edit import TaskMentionTextEdit


class TaskCollaborationDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        store: TaskCollaborationStore | None = None,
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
        self._pending_linked_documents: list[tuple[str, str]] = []
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

        self.presence_label = QLabel("Active now: -")
        self.presence_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        self.presence_label.setWordWrap(True)
        root.addWidget(self.presence_label)

        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        root.addWidget(self.activity_list, 1)

        self.attachments_label = QLabel("Attachments: none")
        self.attachments_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        root.addWidget(self.attachments_label)
        self.linked_documents_label = QLabel("Shared documents: none")
        self.linked_documents_label.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
        root.addWidget(self.linked_documents_label)

        self.comment_input = TaskMentionTextEdit()
        self.comment_input.set_mention_handles([candidate.handle for candidate in self._mention_candidates])
        self.comment_input.setPlaceholderText("Add activity update... (use @username for mentions)")
        self.comment_input.setMinimumHeight(120)
        root.addWidget(self.comment_input)

        row = QHBoxLayout()
        self.btn_add_attachment = QPushButton("Attach File")
        self.btn_link_document = QPushButton("Link Shared Document")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_post = QPushButton("Post Update")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for btn in (
            self.btn_add_attachment,
            self.btn_link_document,
            self.btn_refresh,
            self.btn_post,
            self.btn_close,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)

        self.btn_add_attachment.clicked.connect(self._add_attachment)
        self.btn_link_document.clicked.connect(self._link_shared_document)
        self.btn_refresh.clicked.connect(lambda: self.reload_comments(mark_read=True))
        self.btn_post.clicked.connect(self._post_comment)
        self.btn_close.clicked.connect(self.accept)
        self.btn_add_attachment.setEnabled(self._can_post)
        self.btn_link_document.setEnabled(self._can_post and self._collaboration_service is not None)
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

    def _link_shared_document(self) -> None:
        if self._collaboration_service is None:
            QMessageBox.information(
                self,
                "Shared Documents",
                "Shared document linking requires the service-backed collaboration runtime.",
            )
            return
        try:
            pending_ids = {document_id for document_id, _label in self._pending_linked_documents}
            available_documents = [
                document
                for document in self._collaboration_service.list_available_documents(active_only=True)
                if document.id not in pending_ids
            ]
        except Exception as exc:
            QMessageBox.warning(self, "Shared Documents", str(exc))
            return
        if not available_documents:
            QMessageBox.information(
                self,
                "Shared Documents",
                "No additional active shared documents are available to link.",
            )
            return
        dialog = ProjectManagementDocumentLinkDialog(
            title="Link Shared Document",
            prompt="Select an active shared document to link to the comment you are about to post.",
            document_options=[
                (f"{document.document_code} - {document.title}", document.id)
                for document in available_documents
            ],
            confirm_label="Link Document",
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        document_id = dialog.document_id
        if not document_id:
            return
        self._pending_linked_documents.append((document_id, dialog.document_label()))
        self._refresh_attachment_label()

    def _refresh_attachment_label(self) -> None:
        if not self._pending_attachments:
            self.attachments_label.setText("Attachments: none")
        else:
            names = [Path(path).name for path in self._pending_attachments]
            preview = ", ".join(names[:4]) + ("..." if len(names) > 4 else "")
            self.attachments_label.setText(f"Attachments: {preview}")
        if not self._pending_linked_documents:
            self.linked_documents_label.setText("Shared documents: none")
        else:
            labels = [label for _document_id, label in self._pending_linked_documents]
            preview = ", ".join(labels[:3]) + ("..." if len(labels) > 3 else "")
            self.linked_documents_label.setText(f"Shared documents: {preview}")

    def reload_comments(self, *, mark_read: bool = True) -> None:
        if self._collaboration_service is not None:
            if mark_read:
                self._collaboration_service.mark_task_mentions_read(self._task_id)
            comments = self._comment_rows_from_service(
                self._collaboration_service.list_comments(self._task_id),
                self._collaboration_service.list_comment_documents(self._task_id),
            )
        else:
            if self._store is None:
                raise RuntimeError("Task collaboration storage is not configured.")
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
            linked_documents = [str(item) for item in row.get("linked_documents", [])]
            lines = [f"{author}  [{created_at}]"]
            lines.append(body)
            if mentions:
                lines.append(f"Mentions: {', '.join('@' + m for m in mentions)}")
            if linked_documents:
                lines.append("Linked documents:")
                lines.extend(f"- {item}" for item in linked_documents)
            if attachments:
                lines.append("Attachment references:" if linked_documents else "Attachments:")
                lines.extend(f"- {item}" for item in attachments)
            item = QListWidgetItem("\n".join(lines))
            self.activity_list.addItem(item)
        self._refresh_presence_label()

    def _refresh_presence_label(self) -> None:
        if self._collaboration_service is None:
            self.presence_label.setText("Active now: unavailable in local-only collaboration mode.")
            return
        try:
            rows = self._collaboration_service.list_task_presence(self._task_id)
        except Exception as exc:
            self.presence_label.setText(f"Active now: unavailable ({exc})")
            return
        lines = format_presence_lines(rows, include_self=True)
        self.presence_label.setText(
            "Active now: " + ("; ".join(lines) if lines else "no active collaborators")
        )

    @staticmethod
    def _comment_rows_from_service(
        comments: list[TaskComment],
        documents_by_comment: dict[str, list[object]] | None = None,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for comment in comments:
            rows.append(
                {
                    "author": comment.author_username or "unknown",
                    "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M"),
                    "body": comment.body,
                    "mentions": list(comment.mentions or []),
                    "attachments": list(comment.attachments or []),
                    "linked_documents": [
                        format_linked_document_label(document)
                        for document in (documents_by_comment or {}).get(comment.id, [])
                    ],
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
                    linked_document_ids=[document_id for document_id, _label in self._pending_linked_documents],
                )
            else:
                if self._store is None:
                    raise RuntimeError("Task collaboration storage is not configured.")
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
        self._pending_linked_documents.clear()
        self._refresh_attachment_label()
        # Keep newly posted mentions unread until user explicitly refreshes.
        self.reload_comments(mark_read=False)


__all__ = ["TaskCollaborationDialog"]
