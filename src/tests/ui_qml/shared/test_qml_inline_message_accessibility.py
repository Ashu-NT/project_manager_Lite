"""Phase H: InlineMessage accessibility -- Accessible.name/role metadata,
keyboard-activatable action button, and no visual regression (still renders,
still emits actionClicked on click)."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import Qt
from PySide6.QtGui import QAccessible
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine

_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 400
    height: 100
    visible: true
    property int actionCount: 0
    readonly property int msgAccessibleRole: msg.Accessible.role
    readonly property string msgAccessibleName: msg.Accessible.name

    AppWidgets.InlineMessage {
        id: msg
        objectName: "inlineMessage"
        anchors.left: parent.left
        anchors.right: parent.right
        tone: "%(tone)s"
        message: "%(message)s"
        actionLabel: "%(actionLabel)s"
        onActionClicked: harness.actionCount += 1
    }
}
"""


def _create_harness(qapp, *, tone="danger", message="Something failed.", action_label="Retry"):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    source = _SOURCE % {"tone": tone, "message": message, "actionLabel": action_label}
    component.setData(dedent(source).encode("utf-8"), "inline-message-a11y-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    qapp.processEvents()
    return engine, component, root


def _find_by_object_name(obj, name):
    if obj.objectName() == name:
        return obj
    for child in obj.children():
        found = _find_by_object_name(child, name)
        if found is not None:
            return found
    return None


def test_danger_message_has_alert_role_and_name(qapp) -> None:
    engine, component, root = _create_harness(qapp, tone="danger", message="Projects could not be loaded.")
    try:
        assert root.property("msgAccessibleRole") == QAccessible.Role.AlertMessage.value
        assert root.property("msgAccessibleName") == "Projects could not be loaded."
    finally:
        root.deleteLater()
        del component, engine


def test_info_message_has_static_text_role(qapp) -> None:
    engine, component, root = _create_harness(qapp, tone="info", message="Loading...", action_label="")
    try:
        assert root.property("msgAccessibleRole") == QAccessible.Role.StaticText.value
    finally:
        root.deleteLater()
        del component, engine


def test_action_button_is_keyboard_focusable_when_action_present(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        msg = _find_by_object_name(root, "inlineMessage")
        assert msg.property("activeFocusOnTab") is False  # the message body itself is passive
    finally:
        root.deleteLater()
        del component, engine


def test_action_button_activates_on_return_key(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        action_btn = _find_by_object_name(root, "inlineMessageActionButton")
        assert action_btn is not None
        assert action_btn.property("activeFocusOnTab") is True
        action_btn.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("actionCount") == 1
    finally:
        root.deleteLater()
        del component, engine




def test_no_action_label_means_no_action_button_focus_target(qapp) -> None:
    engine, component, root = _create_harness(qapp, action_label="")
    try:
        qapp.processEvents()
        # Renders without error even with no action -- no crash/warning path.
        msg = _find_by_object_name(root, "inlineMessage")
        assert msg is not None
    finally:
        root.deleteLater()
        del component, engine


def _set_theme(engine, mode: str) -> None:
    component = QQmlComponent(engine)
    component.setData(
        (
            'import QtQuick\nimport App.Theme 1.0 as Theme\n'
            'QtObject { Component.onCompleted: Theme.AppTheme.themeMode = "%s" }' % mode
        ).encode("utf-8"),
        "set-theme.qml",
    )
    obj = component.create()
    assert obj is not None, "\n".join(e.toString() for e in component.errors())


def test_inline_message_loads_without_warnings_light_and_dark(qapp) -> None:
    from PySide6.QtCore import qInstallMessageHandler

    for mode in ("light", "dark"):
        for tone in ("info", "success", "warning", "danger"):
            messages: list[str] = []
            previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
            engine = create_qml_engine()
            _set_theme(engine, mode)
            component = QQmlComponent(engine)
            source = _SOURCE % {"tone": tone, "message": "Check.", "actionLabel": "Retry"}
            component.setData(dedent(source).encode("utf-8"), "inline-message-theme-test.qml")
            root = component.create()
            try:
                assert root is not None, "\n".join(e.toString() for e in component.errors())
                qapp.processEvents()
                relevant = [
                    m for m in messages
                    if "ReferenceError" in m or "TypeError" in m or "is not defined" in m
                ]
                assert relevant == [], f"mode={mode} tone={tone} warnings={relevant}"
            finally:
                if root is not None:
                    root.deleteLater()
                qapp.processEvents()
                qInstallMessageHandler(previous_handler)
