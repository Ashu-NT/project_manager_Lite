"""Live user report against DataTable (the shared widget behind Projects,
Tasks, Portfolio, and most Platform/Maintenance/Inventory list pages):
the header "select all" checkbox didn't work and wasn't centered (it used
a real QQC2.CheckBox Control, unlike the per-row checkboxes which are a
plain Rectangle+Text+MouseArea and worked fine); columns had no resize
affordance; the sort indicator used tiny unicode triangle glyphs instead
of a real icon; header/row text used inconsistent left margins. This
covers the header checkbox and the new column-resize drag with real
QTest mouse simulation, matching this file's established harness style."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QPoint, Qt
from PySide6.QtQml import QJSValue, QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "data-table-header-resize-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _to_py(value):
    return value.toVariant() if isinstance(value, QJSValue) else value


def test_header_select_all_checkbox_click_toggles_all(qapp) -> None:
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
            property var toggledValues: []

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                multiSelect: true
                columns: [{key: "name", label: "Name", flex: 0, minWidth: 200, sortable: true}]
                rows: [{id: "1", name: "Alpha"}, {id: "2", name: "Beta"}]
                selectedRowIds: []
                onSelectAllToggled: function(allSelected) {
                    harness.toggledValues.push(allSelected)
                }
            }
        }
        """,
    )

    # The header checkbox cell is the fixed-width column at the very left
    # of the header row (root._cbColW = 32px) -- click its center.
    QTest.mouseClick(
        root,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(16, 20),
    )
    qapp.processEvents()

    toggled = _to_py(root.property("toggledValues"))
    assert list(toggled) == [True], (
        "header select-all checkbox did not fire selectAllToggled(true) on click"
    )
    root.deleteLater()
    del component, engine


def test_header_select_all_checkbox_toggles_off_when_all_already_selected(qapp) -> None:
    # selectedRowIds is declared already-populated (both row ids) rather
    # than mutated imperatively after construction -- this is the same
    # "all selected" state _allChecked reads, expressed the reliable way.
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
            property var toggledValues: []

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                multiSelect: true
                columns: [{key: "name", label: "Name", flex: 0, minWidth: 200, sortable: true}]
                rows: [{id: "1", name: "Alpha"}, {id: "2", name: "Beta"}]
                selectedRowIds: ["1", "2"]
                onSelectAllToggled: function(allSelected) {
                    harness.toggledValues.push(allSelected)
                }
            }
        }
        """,
    )

    QTest.mouseClick(
        root,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(16, 20),
    )
    qapp.processEvents()

    toggled = _to_py(root.property("toggledValues"))
    assert list(toggled) == [False]
    root.deleteLater()
    del component, engine


def test_column_resize_commits_once_on_release_not_per_move(qapp) -> None:
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
            property int columnsStateChangedCount: 0
            property real lastCommittedWidth: -1

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [
                    {key: "name", label: "Name", flex: 0, minWidth: 100, sortable: true},
                    {key: "status", label: "Status", flex: 0, minWidth: 100}
                ]
                rows: [{id: "1", name: "Alpha", status: "Active"}]
                onColumnsStateChanged: function(cols) {
                    harness.columnsStateChangedCount += 1
                    harness.lastCommittedWidth = cols[0].preferredWidth
                }
            }
        }
        """,
    )

    # Column 0 is 100px wide (flex:0, minWidth:100). The resize handle is
    # right-anchored with width 9, so it spans local x=[91, 100) -- pressing
    # exactly at the column boundary (x=100) lands on the edge shared with
    # column 1's own full-cell sort MouseArea, not reliably inside the
    # handle. Press comfortably inside the handle's own span instead.
    QTest.mousePress(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(96, 20)
    )
    qapp.processEvents()
    QTest.mouseMove(root, QPoint(116, 20))
    qapp.processEvents()
    QTest.mouseMove(root, QPoint(136, 20))
    qapp.processEvents()

    # Still dragging -- must not have committed a model change yet.
    assert root.property("columnsStateChangedCount") == 0

    QTest.mouseRelease(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(136, 20)
    )
    qapp.processEvents()

    assert root.property("columnsStateChangedCount") == 1
    # Dragged +40px (96 -> 136), so the committed width should land at (or
    # very near) 140, not still be 100 and not have driven multiple
    # intermediate commits.
    assert root.property("lastCommittedWidth") >= 130
    root.deleteLater()
    del component, engine


def test_resizing_one_column_does_not_shrink_others(qapp) -> None:
    # Growing column 0 must not shrink column 1 to compensate -- the table
    # scrolls horizontally, so total content width should grow instead.
    # Before this fix, growing one column's base width reduced
    # _extraFlexSpace, which every flex>0 column's share is computed from,
    # so every other column would get visibly narrower as a side effect of
    # resizing just one. col1Width is a live QML binding (re-read after the
    # resize, not snapshotted), so both reads reflect the current state.
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
            readonly property real col1Width: table._visCols.length > 1
                ? table._colWidth(table._visCols[1])
                : -1

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [
                    {key: "name", label: "Name", flex: 0, minWidth: 100, sortable: true},
                    {key: "status", label: "Status", flex: 1, minWidth: 100}
                ]
                rows: [{id: "1", name: "Alpha", status: "Active"}]
            }
        }
        """,
    )

    width_before = root.property("col1Width")
    assert width_before > 100  # flex:1 column filled the remaining ~540px

    QTest.mousePress(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(96, 20)
    )
    qapp.processEvents()
    QTest.mouseMove(root, QPoint(216, 20))
    qapp.processEvents()
    QTest.mouseRelease(
        root, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(216, 20)
    )
    qapp.processEvents()

    width_after = root.property("col1Width")
    assert width_after >= width_before, (
        f"column 1 shrank from {width_before} to {width_after} after "
        "resizing column 0 -- other columns must not compensate"
    )
    root.deleteLater()
    del component, engine
