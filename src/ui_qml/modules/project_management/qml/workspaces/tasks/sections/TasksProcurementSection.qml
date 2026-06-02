pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property bool canOpenProcurement: false
    property bool isBusy: false

    signal openProcurementRequested()

    implicitHeight: _procurementCol.implicitHeight

    ColumnLayout {
        id: _procurementCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Procurement"
            subtitle: root.canOpenProcurement
                ? "Review task-linked requisitions and purchasing commitments."
                : "Procurement requisition capabilities are not enabled."
            busy: root.isBusy
            actions: [
                { "id": "open", "label": "Open Procurement", "icon": "document", "enabled": root.canOpenProcurement, "danger": false }
            ]
            onActionTriggered: function(actionId) {
                if (actionId === "open") root.openProcurementRequested()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            title: "Procurement commitments for this task."
            message: root.canOpenProcurement
                ? "Open Procurement > Requisitions and filter by this task to review linked purchase requests."
                : "Procurement workflows are unavailable because the linked module or capability is disabled."
        }
    }
}
