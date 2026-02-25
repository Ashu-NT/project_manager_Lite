from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from core.services.task import TaskService


def show_overallocation_warning_if_any(parent, task_service: TaskService) -> None:
    consume = getattr(task_service, "consume_last_overallocation_warning", None)
    if not callable(consume):
        return
    warning = consume()
    if warning:
        QMessageBox.information(parent, "Allocation Warning", warning)


__all__ = ["show_overallocation_warning_if_any"]
