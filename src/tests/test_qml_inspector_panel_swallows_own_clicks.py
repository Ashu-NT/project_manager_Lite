"""Follow-up to the DataTable empty-space-click fix: Projects (and 10 other
platform pages) place `AppWidgets.InspectorPanel` next to a list/table inside
a RowLayout, with no background "click outside closes the inspector"
handling at all today. Adding one (done in ProjectsWorkspacePage.qml as a
low-z MouseArea sitting behind the whole list/inspector row) only works if
InspectorPanel itself never lets a click on its own blank padding fall
through to whatever sits behind it -- otherwise "click outside the panel
closes it" would also fire for clicks *inside* the panel's own margins.

This covers that guarantee at the widget level: InspectorPanel now has a
full-fill MouseArea as its first child (see InspectorPanel.qml) that
swallows presses on its own background before they can reach an underlying
catcher, while real controls (the close "X") still work as before."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QPoint, Qt
from PySide6.QtQml import QJSValue, QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "inspector-panel-swallow-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _to_py(value):
    return value.toVariant() if isinstance(value, QJSValue) else value


def _harness_source() -> str:
    return """
    import QtQuick
    import App.Widgets 1.0 as AppWidgets

    Window {
        id: harness
        width: 640
        height: 400
        visible: true
        property int outsideCatcherHits: 0
        property int closeRequestedHits: 0

        // Stands in for a workspace page's "click outside closes the
        // inspector" background catcher, sitting behind the panel.
        MouseArea {
            anchors.fill: parent
            onPressed: harness.outsideCatcherHits += 1
        }

        AppWidgets.InspectorPanel {
            id: panel
            anchors.right: parent.right
            height: parent.height
            title: "Alpha"
            sections: [{label: "Client", value: "Acme Co"}]

            onCloseRequested: harness.closeRequestedHits += 1
        }
    }
    """


def test_click_on_panel_blank_background_does_not_reach_outside_catcher(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())

    # Click well within the panel's body (below the header, above the
    # action buttons) -- blank metadata-section padding, no control there.
    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(600, 200)
    )
    qapp.processEvents()

    assert _to_py(root.property("outsideCatcherHits")) == 0, (
        "a click on InspectorPanel's own blank background must not bleed "
        "through to a catcher sitting behind it"
    )
    assert _to_py(root.property("closeRequestedHits")) == 0

    root.deleteLater()
    del component, engine


def test_click_outside_panel_still_reaches_the_catcher(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())

    # Far left of the window, outside the right-anchored panel entirely.
    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(20, 200)
    )
    qapp.processEvents()

    assert _to_py(root.property("outsideCatcherHits")) == 1
    assert _to_py(root.property("closeRequestedHits")) == 0

    root.deleteLater()
    del component, engine


def test_close_button_still_emits_close_requested(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())

    # The close "X" sits near the top-right of the panel header.
    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(627, 22)
    )
    qapp.processEvents()

    assert _to_py(root.property("closeRequestedHits")) == 1
    assert _to_py(root.property("outsideCatcherHits")) == 0

    root.deleteLater()
    del component, engine
