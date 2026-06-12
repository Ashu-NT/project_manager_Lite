from __future__ import annotations

import logging
from time import perf_counter

from PySide6.QtCore import QObject, QRunnable, Signal

from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)

logger = logging.getLogger(__name__)


class TaskDetailWorkerSignals(QObject):
    finished = Signal(object)  # emits (request_id: int, workspace_state)
    failed = Signal(object)    # emits (request_id: int, error_message: str)


class TaskDetailWorker(QRunnable):
    """Runs build_task_basic_detail_state in a thread-pool thread."""

    def __init__(
        self,
        *,
        presenter: ProjectTasksWorkspacePresenter,
        task_id: str,
        project_id: str | None,
        request_id: int,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._signals = TaskDetailWorkerSignals()
        self._presenter = presenter
        self._task_id = task_id
        self._project_id = project_id
        self._request_id = request_id

    @property
    def signals(self) -> TaskDetailWorkerSignals:
        return self._signals

    def run(self) -> None:
        started = perf_counter()
        logger.debug(
            "PM task detail worker start request_id=%s task_id=%s project_id=%s",
            self._request_id,
            self._task_id,
            self._project_id or "-",
        )
        try:
            ws = self._presenter.build_task_basic_detail_state(
                task_id=self._task_id,
                project_id=self._project_id,
            )
            logger.info(
                "PM task detail worker complete request_id=%s task_id=%s duration_ms=%.1f",
                self._request_id,
                self._task_id,
                (perf_counter() - started) * 1000,
            )
            self._signals.finished.emit((self._request_id, ws))
        except Exception as exc:
            logger.exception(
                "PM task detail worker failed request_id=%s task_id=%s project_id=%s duration_ms=%.1f",
                self._request_id,
                self._task_id,
                self._project_id or "-",
                (perf_counter() - started) * 1000,
            )
            self._signals.failed.emit((self._request_id, str(exc)))


__all__ = ["TaskDetailWorker", "TaskDetailWorkerSignals"]
