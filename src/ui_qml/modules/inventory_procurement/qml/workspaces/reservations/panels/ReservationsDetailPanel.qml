pragma ComponentBehavior: Bound
import QtQuick
import "../../inventory/panels"

Item {
    id: root

    property var detailPage: null
    property var reservationDetail: ({ "fields": [], "emptyState": "Select a reservation to view details." })
    property var activityItems: []

    width:          parent ? parent.width : 0
    implicitHeight: _panel.implicitHeight

    InventoryDetailPanel {
        id: _panel
        anchors.left:  parent.left
        anchors.right: parent.right
        detailPage:    root.detailPage
        fields:        root.reservationDetail.fields || []
        activityItems: root.activityItems
        emptyState:    root.reservationDetail.emptyState || "No details available."
    }
}
