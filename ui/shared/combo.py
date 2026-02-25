from __future__ import annotations

from PySide6.QtWidgets import QComboBox


def current_data(combo: QComboBox) -> str | None:
    idx = combo.currentIndex()
    if idx < 0:
        return None
    return combo.itemData(idx)


def current_data_and_text(combo: QComboBox) -> tuple[str | None, str | None]:
    idx = combo.currentIndex()
    if idx < 0:
        return None, None
    return combo.itemData(idx), combo.currentText()


__all__ = ["current_data", "current_data_and_text"]
