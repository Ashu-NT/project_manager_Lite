from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class InventoryItemDocumentLinkDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        prompt: str,
        document_options: list[tuple[str, str]],
        confirm_label: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        layout = QVBoxLayout(self)

        prompt_label = QLabel(prompt)
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        self.document_combo = QComboBox()
        for label, document_id in document_options:
            self.document_combo.addItem(label, document_id)
        layout.addWidget(self.document_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.confirm_button = buttons.addButton(confirm_label, QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_actions()
        self.document_combo.currentIndexChanged.connect(self._sync_actions)

    @property
    def document_id(self) -> str:
        value = self.document_combo.currentData()
        return str(value or "").strip()

    def _sync_actions(self) -> None:
        self.confirm_button.setEnabled(bool(self.document_id))


__all__ = ["InventoryItemDocumentLinkDialog"]
