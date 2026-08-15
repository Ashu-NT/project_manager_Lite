"""Live user report against DataTable (the shared widget behind Projects,
Tasks, Portfolio, and most Platform/Maintenance/Inventory list pages):
clicking anywhere other than the inspector panel should close it -- i.e.
clicking blank space in the list clears row selection -- but this stopped
working. Root cause: `_emptySpaceCatcher`'s `anchors.fill: parent` resolved
to the TableView's `contentItem` (a Flickable reparents plain children
into `contentItem` via its default `data` property), whose size is the
scrollable CONTENT size, not the viewport. With only a few rows,
contentHeight is far smaller than the visible viewport, so the catcher
was confined to a small strip near the top and the rest of the visibly-
empty viewport below it received no click handling at all. Fixed by
explicitly overriding `parent: _mainView` and sizing to `_mainView.width`/
`height` so the catcher always spans the full viewport regardless of row
count, and stays put (doesn't scroll with contentY)."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QPoint, Qt
from PySide6.QtQml import QJSValue, QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "data-table-empty-space-click-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _to_py(value):
    return value.toVariant() if isinstance(value, QJSValue) else value


def test_clicking_blank_space_below_a_few_rows_clears_selection(qapp) -> None:
    # Only 2 short rows in a 240px-tall window -- contentHeight is far
    # smaller than the viewport, reproducing the exact scenario where the
    # bug hid: plenty of visibly-empty space below the last row.
    engine, component, root = _create_harness(
        qapp,
        """
        import QtQuick
        import App.Widgets 1.0 as AppWidgets

        Window {
            id: harness
            width: 640
            height: 240
            visible: true
            property var selections: []

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", flex: 0, minWidth: 200}]
                rows: [{id: "1", name: "Alpha"}, {id: "2", name: "Beta"}]
                selectedRowId: ""
                onRowSelected: function(rowId) { harness.selections.push(rowId) }
            }
        }
        """,
    )

    # Row 0 sits just below the header (~44px); click inside it first so
    # there is a real selection to clear.
    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(100, 55)
    )
    qapp.processEvents()
    assert _to_py(root.property("selections")) == ["1"]

    # Click far below both rows, well within the window but well beyond
    # the table's actual (short) content height.
    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(100, 200)
    )
    qapp.processEvents()
    assert _to_py(root.property("selections")) == ["1", ""], (
        "clicking visibly-empty space below a short row list must clear "
        "selection (closing any open inspector) -- it did not fire at all"
    )
    root.deleteLater()
    del component, engine


def test_clicking_a_row_still_selects_it_not_swallowed_by_empty_catcher(qapp) -> None:
    # Guards against a naive fix that makes the (now viewport-sized) empty-
    # space catcher swallow clicks meant for actual rows instead of falling
    # through to them.
    engine, component, root = _create_harness(
        qapp,
        """
        import QtQuick
        import App.Widgets 1.0 as AppWidgets

        Window {
            id: harness
            width: 640
            height: 240
            visible: true
            property var selections: []

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", flex: 0, minWidth: 200}]
                rows: [{id: "1", name: "Alpha"}, {id: "2", name: "Beta"}]
                selectedRowId: ""
                onRowSelected: function(rowId) { harness.selections.push(rowId) }
            }
        }
        """,
    )

    QTest.mouseClick(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(100, 55)
    )
    qapp.processEvents()

    assert _to_py(root.property("selections")) == ["1"]
    root.deleteLater()
    del component, engine
