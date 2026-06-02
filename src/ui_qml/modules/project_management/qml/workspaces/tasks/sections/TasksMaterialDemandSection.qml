pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var taskDetail: ({ "state": {} })
    property bool canOpenReservations: false
    property bool canOpenProcurement: false
    property bool isBusy: false

    signal openReservationsRequested()
    signal openProcurementRequested()

    implicitHeight: _materialCol.implicitHeight

    ColumnLayout {
        id: _materialCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Material Demand"
            subtitle: String(root.taskDetail.state.materialDemandLabel || "").length > 0
                ? String(root.taskDetail.state.materialDemandLabel || "")
                : (root.canOpenReservations
                    ? "Open Inventory reservations for linked stock demand."
                    : "Task-linked material demand follows Inventory module availability.")
            busy: root.isBusy
            actions: [
                { "id": "reservations", "label": "Open Reservations", "icon": "storage", "enabled": root.canOpenReservations, "danger": false },
                { "id": "procurement", "label": "Open Procurement", "icon": "document", "enabled": root.canOpenProcurement, "danger": false }
            ]
            onActionTriggered: function(actionId) {
                if (actionId === "reservations") root.openReservationsRequested()
                else if (actionId === "procurement") root.openProcurementRequested()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            title: "Task material demand is managed through Inventory."
            message: root.canOpenReservations
                ? "Use Inventory > Reservations to review and manage stock demand linked to this task. Active: "
                    + String(root.taskDetail.state.materialDemandActive || "0")
                    + ", fulfilled: "
                    + String(root.taskDetail.state.materialDemandFulfilled || "0")
                    + ", closed: "
                    + String(root.taskDetail.state.materialDemandCancelled || "0")
                    + "."
                : "Inventory reservation capabilities are not enabled for this workspace."
        }
    }
}
