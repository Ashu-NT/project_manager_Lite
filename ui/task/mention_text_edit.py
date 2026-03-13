from __future__ import annotations

import re

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QCompleter, QTextEdit


_MENTION_PREFIX_RE = re.compile(r"(?:^|[\s(])@([A-Za-z0-9_.-]{1,64})$")


class TaskMentionTextEdit(QTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mention_handles: list[str] = []
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setModel(QStringListModel([], self._completer))
        self._completer.activated.connect(self._insert_completion)

    def set_mention_handles(self, handles: list[str]) -> None:
        self._mention_handles = sorted({str(item).strip().lower() for item in handles if str(item).strip()})
        model = self._completer.model()
        if isinstance(model, QStringListModel):
            model.setStringList(self._mention_handles)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        popup = self._completer.popup()
        if popup.isVisible() and event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Backtab):
            event.ignore()
            return
        if popup.isVisible() and event.key() == Qt.Key_Escape:
            popup.hide()
            event.accept()
            return

        super().keyPressEvent(event)
        self._sync_completion_popup()

    def _sync_completion_popup(self) -> None:
        prefix = self._current_mention_prefix()
        if not prefix:
            self._completer.popup().hide()
            return
        self._completer.setCompletionPrefix(prefix)
        if self._completer.completionCount() <= 0:
            self._completer.popup().hide()
            return
        rect = self.cursorRect()
        rect.setWidth(max(240, self._completer.popup().sizeHintForColumn(0) + 24))
        self._completer.complete(rect)

    def _current_mention_prefix(self) -> str:
        cursor = self.textCursor()
        text_before_cursor = self.toPlainText()[: cursor.position()]
        match = _MENTION_PREFIX_RE.search(text_before_cursor)
        return str(match.group(1) or "").strip().lower() if match else ""

    def _insert_completion(self, completion: str) -> None:
        prefix = self._current_mention_prefix()
        if not prefix:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(prefix))
        cursor.insertText(str(completion))
        cursor.insertText(" ")
        self.setTextCursor(cursor)


__all__ = ["TaskMentionTextEdit"]
