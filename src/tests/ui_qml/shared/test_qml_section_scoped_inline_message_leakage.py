"""Regression coverage for a reported InlineMessage leakage bug:
SectionScopedInlineMessage remembers which section a message belonged to
and hides it while any other section is active -- but it never forgot that
association, so navigating away and back to the same section resurrected a
stale, possibly long-outdated message. It now "consumes" the message the
first time the user navigates away from its section, so it never reappears
on a later return -- only a genuinely new message may show again."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: harness
    width: 400
    height: 200

    property int activeSectionIndex: 0
    property var sections: [{"label": "A"}, {"label": "B"}]
    property bool isBusy: false
    function scrollToSection(index) { harness.activeSectionIndex = index }

    property alias message: msg.message
    readonly property bool msgVisible: msg.visible

    AppWidgets.SectionScopedInlineMessage {
        id: msg
        objectName: "scopedMessage"
        detailPage: harness
        tone: "danger"
        message: ""
    }
}
"""


def _pump(n: int = 5) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def _create_harness(qapp):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(_SOURCE).encode("utf-8"), "section-scoped-inline-message-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
    _pump()
    return engine, component, root


def test_message_hides_on_other_section_and_does_not_reappear_on_return(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        assert root.property("activeSectionIndex") == 0

        root.setProperty("message", "Something failed on section A.")
        _pump()
        assert root.property("msgVisible") is True

        # Navigate away -- correctly hidden (existing behavior).
        root.setProperty("activeSectionIndex", 1)
        _pump()
        assert root.property("msgVisible") is False

        # Navigate back -- must NOT resurrect the stale message.
        root.setProperty("activeSectionIndex", 0)
        _pump()
        assert root.property("msgVisible") is False, (
            "a message must not reappear just because the user returned to "
            "the section it was originally shown for"
        )

        # A genuinely new message must still show normally.
        root.setProperty("message", "")
        _pump()
        root.setProperty("message", "A brand new failure on section A.")
        _pump()
        assert root.property("msgVisible") is True
    finally:
        root.deleteLater()
        QCoreApplication.processEvents()


def test_message_still_shows_on_first_visit_to_its_own_section(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        root.setProperty("message", "Failure while on section A.")
        _pump()
        assert root.property("msgVisible") is True
        assert root.property("activeSectionIndex") == 0
    finally:
        root.deleteLater()
        QCoreApplication.processEvents()
