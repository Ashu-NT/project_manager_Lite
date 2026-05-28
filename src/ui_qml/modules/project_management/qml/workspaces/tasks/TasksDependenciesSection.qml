pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var    dependenciesModel: AppMock.MockFactory.catalog()
    property bool   isBusy:           false
    property bool   canCreate:        false
    property string errorText:        ""

    signal createRequested()
    signal deleteRequested(var dependencyData)

    readonly property var    _items: root.dependenciesModel.items || []
    property string          _selectedId: ""
    readonly property var    _selectedItem: {
        const id = root._selectedId
        if (!id) return null
        const list = root._items
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === id) return list[i]
        }
        return null
    }

    readonly property int _tableH: {
        const n = root._items.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 280)
    }

    readonly property var _columns: [
        { key: "title",       label: "Task",   flex: 3,   sortable: false },
        { key: "subtitle",    label: "Type",   flex: 1.5, sortable: false },
        { key: "metaText",    label: "Lag",    flex: 1,   sortable: false },
        { key: "statusLabel", label: "Status", flex: 0,   minWidth: 90, type: "status" }
    ]

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left:  parent.left
        anchors.right: parent.right
        anchors.top:   parent.top
        spacing: 0

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
        }

        // Section toolbar — idle
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible:  !root._selectedId
            title:    "Dependencies"
            subtitle: root._items.length > 0 ? String(root._items.length) : ""
            busy:     root.isBusy
            createLabel: root.canCreate ? "Add Dependency" : ""
            actions: []
            onCreateRequested: root.createRequested()
        }

        // Section toolbar — row selected
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible:  Boolean(root._selectedId)
            showBack: true
            title:    root._selectedItem ? String(root._selectedItem.title || "Dependency") : "Dependency"
            subtitle: root._selectedItem ? String(root._selectedItem.subtitle || "") : ""
            busy:     root.isBusy
            actions: [
                { id: "remove", label: "Remove", icon: "delete", enabled: true, danger: true }
            ]
            onBackRequested: root._selectedId = ""
            onActionTriggered: function(actionId) {
                if (actionId === "remove" && root._selectedItem)
                    root.deleteRequested(root._selectedItem)
            }
        }

        // DataTable
        Item {
            Layout.fillWidth: true
            height: root._tableH

            AppWidgets.DataTable {
                anchors.fill:  parent
                columns:       root._columns
                rows:          root._items
                selectedRowId: root._selectedId
                loading:       root.isBusy
                emptyText:     root.dependenciesModel.emptyState || "No dependencies for this task."

                onRowSelected: function(rowId) { root._selectedId = rowId }
                onRowActivated: function(rowId) { root._selectedId = rowId }
            }
        }
    }
}
