from __future__ import annotations

import re
from uuid import uuid4
from typing import Callable

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QWidget

from src.ui.shared.formatting.ui_config import UIConfig as CFG


def suggest_generated_code(prefix: str, *hint_values: str) -> str:
    normalized_prefix = _normalize_code_token(prefix, fallback="CODE", max_length=8)
    hint_token = ""
    for value in hint_values:
        hint_token = _normalize_code_token(value, fallback="", max_length=4)
        if hint_token:
            break
    suffix = uuid4().hex[:6].upper()
    if hint_token:
        return f"{normalized_prefix}-{hint_token}-{suffix}"
    return f"{normalized_prefix}-{suffix}"


class CodeFieldWidget(QWidget):
    def __init__(
        self,
        *,
        prefix: str,
        line_edit: QLineEdit | None = None,
        hint_getters: tuple[Callable[[], str], ...] | list[Callable[[], str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.line_edit = line_edit or QLineEdit(self)
        self._prefix = prefix
        self._hint_getters = list(hint_getters or [])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(CFG.SPACING_XS)
        layout.addWidget(self.line_edit, 1)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setFixedHeight(CFG.INPUT_HEIGHT)
        self.generate_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.generate_button.clicked.connect(self.generate_code)
        layout.addWidget(self.generate_button)
        self.setFocusProxy(self.line_edit)

    def generate_code(self) -> None:
        hints = [self._safe_hint_value(getter) for getter in self._hint_getters]
        self.line_edit.setText(suggest_generated_code(self._prefix, *hints))

    def set_hint_getters(self, *hint_getters) -> None:
        self._hint_getters = list(hint_getters)

    @staticmethod
    def _safe_hint_value(getter) -> str:
        try:
            return str(getter() or "").strip()
        except Exception:
            return ""


def _normalize_code_token(value: str, *, fallback: str, max_length: int) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "", str(value or "").strip().upper())
    normalized = normalized[:max_length]
    return normalized or fallback


__all__ = ["CodeFieldWidget", "suggest_generated_code"]
