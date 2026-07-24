pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var tableModel: null
    property var columns: []
    property bool loading: false
    property string emptyText: "No work orders found."
    property string selectedRowId: ""

    signal rowActivated(string rowId)
    signal rowSelected(string rowId)

    width:          parent ? parent.width : 0
    implicitHeight: _table.implicitHeight

    AppWidgets.DataTable {
        id: _table
        anchors.left:  parent.left
        anchors.right: parent.right
        sourceModel:   root.tableModel
        columns:       root.columns
        loading:       root.loading
        emptyText:     root.emptyText
        selectedRowId: root.selectedRowId

        onRowActivated: function(rowId) { root.rowActivated(rowId) }
        onRowSelected:  function(rowId) { root.rowSelected(rowId) }
    }
}
