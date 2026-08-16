from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import (
    Property,
    QAbstractTableModel,
    QPoint,
    QModelIndex,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


ASCENDING = Qt.SortOrder.AscendingOrder.value
DESCENDING = Qt.SortOrder.DescendingOrder.value


class _SortSpyModel(QAbstractTableModel):
    columnsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._columns: list[dict] = []
        self.toggle_count = 0
        self.last_key = ""

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if not parent.isValid() else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if not parent.isValid() else 0

    def _get_columns(self) -> list[dict]:
        return self._columns

    def _set_columns(self, value: list[dict]) -> None:
        self._columns = list(value or [])
        self.columnsChanged.emit()

    columns = Property(
        "QVariantList",
        _get_columns,
        _set_columns,
        notify=columnsChanged,
    )

    @Property(int, constant=True)
    def rowCountValue(self) -> int:  # noqa: N802
        return 0

    @Slot(str)
    def toggleSort(self, key: str) -> None:  # noqa: N802
        self.toggle_count += 1
        self.last_key = key

    @Slot(int, result=str)
    def rowId(self, _row: int) -> str:  # noqa: N802
        return ""


def _create_harness(qapp, source: str, *, spy_model=None):
    engine = create_qml_engine()
    if spy_model is not None:
        engine.rootContext().setContextProperty("spyModel", spy_model)
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "data-table-runtime-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _click_first_header(root, qapp) -> None:
    QTest.mouseClick(
        root,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(80, 20),
    )
    qapp.processEvents()


def test_server_sort_request_preserves_authoritative_qml_bindings(qapp) -> None:
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
            property string controllerSortKey: "name"
            property int controllerSortDirection: Qt.AscendingOrder
            property string requestedKey: ""
            property int requestedDirection: -1
            property int requestCount: 0
            readonly property string tableSortKey: table.sortKey
            readonly property int tableSortDirection: table.sortDirection

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", sortable: true}]
                rows: [{id: "2", name: "Zulu"}, {id: "1", name: "Alpha"}]
                sortingMode: "server"
                sortKey: harness.controllerSortKey
                sortDirection: harness.controllerSortDirection
                onSortRequested: function(key, direction) {
                    harness.requestedKey = key
                    harness.requestedDirection = direction
                    harness.requestCount += 1
                }
            }
        }
        """,
    )

    _click_first_header(root, qapp)

    assert root.property("requestedKey") == "name"
    assert root.property("requestedDirection") == DESCENDING
    assert root.property("requestCount") == 1
    assert root.property("controllerSortKey") == "name"
    assert root.property("controllerSortDirection") == ASCENDING
    assert root.property("tableSortKey") == "name"
    assert root.property("tableSortDirection") == ASCENDING

    root.setProperty("controllerSortKey", "status")
    root.setProperty("controllerSortDirection", DESCENDING)
    qapp.processEvents()

    assert root.property("tableSortKey") == "status"
    assert root.property("tableSortDirection") == DESCENDING
    root.deleteLater()
    del component, engine


def test_invalid_sorting_mode_is_none_and_never_sorts(qapp) -> None:
    spy_model = _SortSpyModel()
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
            property int requestCount: 0
            readonly property string effectiveMode: table._effectiveSortingMode
            readonly property string firstDisplayName: table._displayRows[0].name

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", sortable: true}]
                rows: [{id: "2", name: "Zulu"}, {id: "1", name: "Alpha"}]
                sourceModel: spyModel
                sortingMode: "invalid"
                sortKey: "name"
                sortDirection: Qt.AscendingOrder
                onSortRequested: function() { harness.requestCount += 1 }
            }
        }
        """,
        spy_model=spy_model,
    )

    assert root.property("effectiveMode") == "none"
    assert root.property("firstDisplayName") == "Zulu"
    _click_first_header(root, qapp)
    assert root.property("requestCount") == 0
    assert spy_model.toggle_count == 0
    root.deleteLater()
    del component, engine


def test_server_mode_respects_column_sortable_flag(qapp) -> None:
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
            property int requestCount: 0

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", sortable: false}]
                sortingMode: "server"
                onSortRequested: function() { harness.requestCount += 1 }
            }
        }
        """,
    )

    _click_first_header(root, qapp)
    assert root.property("requestCount") == 0
    root.deleteLater()
    del component, engine


def test_legacy_client_side_sorting_true_keeps_local_sorting(qapp) -> None:
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
            readonly property string effectiveMode: table._effectiveSortingMode
            readonly property string firstDisplayName: table._displayRows[0].name

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", sortable: true}]
                rows: [{id: "2", name: "Zulu"}, {id: "1", name: "Alpha"}]
                clientSideSorting: true
            }
        }
        """,
    )

    assert root.property("effectiveMode") == "client"
    assert root.property("firstDisplayName") == "Zulu"
    _click_first_header(root, qapp)
    assert root.property("firstDisplayName") == "Alpha"
    root.deleteLater()
    del component, engine


def test_legacy_client_side_sorting_false_disables_sorting(qapp) -> None:
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
            property int requestCount: 0
            readonly property string effectiveMode: table._effectiveSortingMode
            readonly property string firstDisplayName: table._displayRows[0].name

            AppWidgets.DataTable {
                id: table
                anchors.fill: parent
                columns: [{key: "name", label: "Name", sortable: true}]
                rows: [{id: "2", name: "Zulu"}, {id: "1", name: "Alpha"}]
                clientSideSorting: false
                onSortRequested: function() { harness.requestCount += 1 }
            }
        }
        """,
    )

    assert root.property("effectiveMode") == "none"
    _click_first_header(root, qapp)
    assert root.property("firstDisplayName") == "Zulu"
    assert root.property("requestCount") == 0
    root.deleteLater()
    del component, engine
