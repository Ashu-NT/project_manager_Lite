from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt

from src.ui_qml.shell.runtime_session import ShellRuntimeSessionController


class _SignalProbe:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, value) -> None:
        for callback in tuple(self._callbacks):
            callback(value)


class _FakeApplication:
    def __init__(self) -> None:
        self.applicationStateChanged = _SignalProbe()
        self.state = Qt.ApplicationState.ApplicationActive

    def applicationState(self):
        return self.state


class _FakeUserSession:
    def __init__(self) -> None:
        self.principal = SimpleNamespace(
            username="planner",
            display_name="Project Planner",
        )

    def is_authenticated(self) -> bool:
        return True


def test_runtime_session_emits_heartbeat_only_while_application_is_active(monkeypatch):
    monkeypatch.setattr(
        "src.ui_qml.shell.runtime_session.update_shell_runtime_state",
        lambda *args, **kwargs: None,
    )
    app = _FakeApplication()
    controller = ShellRuntimeSessionController(
        shell_context=object(),
        user_session=_FakeUserSession(),
        login_prompt=lambda _username: False,
        app=app,
    )
    heartbeats: list[bool] = []
    controller.runtimeHeartbeat.connect(lambda: heartbeats.append(True))

    controller.revalidateSession()
    assert heartbeats == [True]

    app.state = Qt.ApplicationState.ApplicationInactive
    controller.revalidateSession()
    assert heartbeats == [True]

    app.state = Qt.ApplicationState.ApplicationActive
    app.applicationStateChanged.emit(app.state)
    assert heartbeats == [True, True]
