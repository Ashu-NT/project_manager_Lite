from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Generic, TypeVar

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget


_T = TypeVar("_T")


class JobCancelledError(RuntimeError):
    """Raised by background jobs when cancellation is requested."""


class CancelToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise JobCancelledError("Operation canceled by user.")


class _JobSignals(QObject):
    progress = Signal(int, str)
    success = Signal(object)
    failure = Signal(str)
    cancelled = Signal()


class _JobRunnable(QRunnable):
    def __init__(
        self,
        *,
        token: CancelToken,
        work: Callable[[CancelToken, Callable[[int | None, str | None], None]], object],
        signals: _JobSignals,
    ) -> None:
        super().__init__()
        self._token = token
        self._work = work
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._work(self._token, self._emit_progress)
        except JobCancelledError:
            self._signals.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            self._signals.failure.emit(str(exc))
        else:
            if self._token.is_cancelled():
                self._signals.cancelled.emit()
            else:
                self._signals.success.emit(result)

    def _emit_progress(self, percent: int | None, message: str | None) -> None:
        if percent is None:
            value = -1
        else:
            value = max(0, min(100, int(percent)))
        self._signals.progress.emit(value, (message or "").strip())


@dataclass(frozen=True)
class JobUiConfig:
    title: str
    label: str
    cancel_label: str = "Cancel"
    allow_retry: bool = False
    show_progress: bool = True


class AsyncJobHandle(Generic[_T], QObject):
    def __init__(
        self,
        *,
        parent: QWidget,
        ui: JobUiConfig,
        work: Callable[[CancelToken, Callable[[int | None, str | None], None]], _T],
        on_success: Callable[[_T], None],
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        set_busy: Callable[[bool], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._ui = ui
        self._work = work
        self._on_success = on_success
        self._on_error = on_error
        self._on_cancel = on_cancel
        self._set_busy = set_busy
        self._on_finished = on_finished

        self._token: CancelToken | None = None
        self._signals: _JobSignals | None = None
        self._dialog: QProgressDialog | None = None

    def start(self) -> None:
        self._token = CancelToken()
        self._signals = _JobSignals()
        self._signals.progress.connect(self._handle_progress)
        self._signals.success.connect(self._handle_success)
        self._signals.failure.connect(self._handle_failure)
        self._signals.cancelled.connect(self._handle_cancelled)

        if self._ui.show_progress:
            self._dialog = QProgressDialog(
                self._ui.label,
                self._ui.cancel_label,
                0,
                0,
                self._parent,
            )
            self._dialog.setWindowTitle(self._ui.title)
            self._dialog.setWindowModality(Qt.WindowModal)
            self._dialog.setAutoClose(False)
            self._dialog.setAutoReset(False)
            self._dialog.canceled.connect(self._request_cancel)
            self._dialog.show()

        if self._set_busy is not None:
            self._set_busy(True)

        runnable = _JobRunnable(
            token=self._token,
            work=self._work,
            signals=self._signals,
        )
        QThreadPool.globalInstance().start(runnable)

    def _request_cancel(self) -> None:
        if self._token is None:
            return
        self._token.cancel()
        if self._dialog is not None:
            self._dialog.setLabelText("Cancel requested. Finishing current step...")

    def _handle_progress(self, percent: int, message: str) -> None:
        if self._dialog is None:
            return
        if percent < 0:
            self._dialog.setRange(0, 0)
        else:
            if self._dialog.maximum() == 0:
                self._dialog.setRange(0, 100)
            self._dialog.setValue(percent)
        if message:
            self._dialog.setLabelText(message)

    def _handle_success(self, result: object) -> None:
        try:
            self._on_success(result)  # type: ignore[arg-type]
        finally:
            self._finish()

    def _handle_failure(self, message: str) -> None:
        retry_selected = False
        if self._ui.allow_retry:
            button = QMessageBox.warning(
                self._parent,
                self._ui.title,
                message or "Operation failed.",
                QMessageBox.Retry | QMessageBox.Close,
                QMessageBox.Retry,
            )
            retry_selected = button == QMessageBox.Retry
        else:
            if self._on_error is None:
                QMessageBox.warning(self._parent, self._ui.title, message or "Operation failed.")
            else:
                self._on_error(message or "Operation failed.")

        self._finish()
        if retry_selected:
            self.start()

    def _handle_cancelled(self) -> None:
        try:
            if self._on_cancel is not None:
                self._on_cancel()
        finally:
            self._finish()

    def _finish(self) -> None:
        if self._set_busy is not None:
            self._set_busy(False)
        if self._dialog is not None:
            self._dialog.close()
            self._dialog.deleteLater()
            self._dialog = None
        if self._on_finished is not None:
            self._on_finished()


def start_async_job(
    *,
    parent: QWidget,
    ui: JobUiConfig,
    work: Callable[[CancelToken, Callable[[int | None, str | None], None]], _T],
    on_success: Callable[[_T], None],
    on_error: Callable[[str], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    set_busy: Callable[[bool], None] | None = None,
) -> AsyncJobHandle[_T]:
    handles = getattr(parent, "_async_job_handles", None)
    if handles is None:
        handles = []
        setattr(parent, "_async_job_handles", handles)

    handle: AsyncJobHandle[_T] | None = None

    def _cleanup() -> None:
        nonlocal handle
        existing = getattr(parent, "_async_job_handles", [])
        if handle is not None and handle in existing:
            existing.remove(handle)

    handle = AsyncJobHandle(
        parent=parent,
        ui=ui,
        work=work,
        on_success=on_success,
        on_error=on_error,
        on_cancel=on_cancel,
        set_busy=set_busy,
        on_finished=_cleanup,
    )

    handles.append(handle)
    handle.start()
    return handle


__all__ = [
    "AsyncJobHandle",
    "CancelToken",
    "JobCancelledError",
    "JobUiConfig",
    "start_async_job",
]
