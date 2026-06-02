pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../../../inventory/panels"

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property var detailPage: null
    property bool isStoreroomsView: true
    property var storeroomFields:   []
    property var locationFields:    []

    readonly property var _fields: root.isStoreroomsView ? root.storeroomFields : root.locationFields

    width:          parent ? parent.width : 0
    implicitHeight: _panel.implicitHeight

    InventoryDetailPanel {
        id: _panel
        anchors.left:  parent.left
        anchors.right: parent.right
        detailPage:    root.detailPage
        fields:        root._fields
        activityItems: []
        emptyState:    "No details available."
    }
}
