from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QWidget


def handle_stale_write(
    parent: QWidget,
    *,
    title: str,
    entity_label: str,
    reload_callback: Callable[[], None],
) -> None:
    reload_callback()
    QMessageBox.information(
        parent,
        title,
        (
            f"This {entity_label} was updated by another user. "
            "The latest version has been reloaded. Review the changes and try again."
        ),
    )


__all__ = ["handle_stale_write"]
