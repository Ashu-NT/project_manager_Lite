from __future__ import annotations

from ui.platform.shared.async_job import CancelToken, JobCancelledError, _JobRunnable


class _DeletedEmitter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def emit(self, *args: object) -> None:
        self.calls.append(args)
        raise RuntimeError("Signal source has been deleted")


class _DeletedSignals:
    def __init__(self) -> None:
        self.progress = _DeletedEmitter()
        self.success = _DeletedEmitter()
        self.failure = _DeletedEmitter()
        self.cancelled = _DeletedEmitter()


def test_job_runnable_ignores_deleted_signal_source_on_success() -> None:
    signals = _DeletedSignals()

    def _work(token: CancelToken, publish) -> str:
        publish(25, "Loading")
        token.raise_if_cancelled()
        return "done"

    runnable = _JobRunnable(token=CancelToken(), work=_work, signals=signals)

    runnable.run()

    assert signals.progress.calls == [(25, "Loading")]
    assert signals.success.calls == [("done",)]


def test_job_runnable_ignores_deleted_signal_source_on_failure() -> None:
    signals = _DeletedSignals()

    def _work(_token: CancelToken, _publish) -> str:
        raise ValueError("boom")

    runnable = _JobRunnable(token=CancelToken(), work=_work, signals=signals)

    runnable.run()

    assert signals.failure.calls == [("boom",)]


def test_job_runnable_ignores_deleted_signal_source_on_cancelled() -> None:
    signals = _DeletedSignals()

    def _work(_token: CancelToken, _publish) -> str:
        raise JobCancelledError("cancelled")

    runnable = _JobRunnable(token=CancelToken(), work=_work, signals=signals)

    runnable.run()

    assert signals.cancelled.calls == [()]
