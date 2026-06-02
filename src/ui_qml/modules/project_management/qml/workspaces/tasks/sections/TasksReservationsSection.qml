pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var taskDetail: ({ "state": {} })
    property bool canOpenReservations: false
    property bool isBusy: false

    signal openReservationsRequested()

    implicitHeight: _reservationsCol.implicitHeight

    ColumnLayout {
        id: _reservationsCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Reservations"
            subtitle: String(root.taskDetail.state.materialDemandLabel || "").length > 0
                ? String(root.taskDetail.state.materialDemandLabel || "")
                : (root.canOpenReservations
                    ? "Review linked stock reservations in Inventory."
                    : "Inventory reservation capabilities are not enabled.")
            busy: root.isBusy
            actions: [
                { "id": "open", "label": "Open Reservations", "icon": "storage", "enabled": root.canOpenReservations, "danger": false }
            ]
            onActionTriggered: function(actionId) {
                if (actionId === "open") root.openReservationsRequested()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            title: "Stock reservations linked to this task."
            message: root.canOpenReservations
                ? "Open Inventory > Reservations and filter by this task to review or create reservations. Total linked reservations: "
                    + String(root.taskDetail.state.materialDemandTotal || "0")
                    + "."
                : "Inventory reservations are unavailable because the linked module or capability is disabled."
        }
    }
}
