from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt


def horizontal_header_data(
    headers: list[str],
    section: int,
    orientation,
    role,
    fallback: Callable[[int, object, int], object],
):
    if orientation == Qt.Horizontal and role == Qt.DisplayRole:
        return headers[section]
    return fallback(section, orientation, role)


__all__ = ["horizontal_header_data"]
