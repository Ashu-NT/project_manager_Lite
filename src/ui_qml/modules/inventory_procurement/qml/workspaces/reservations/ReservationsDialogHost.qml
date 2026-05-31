import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var createTarget: ({})
    property var issueTarget: ({})
    property var confirmationTarget: ({})
    property string confirmationMode: ""

    signal createReservationRequested(var payload)
    signal issueReservationRequested(var payload)
    signal releaseReservationRequested(string reservationId)
    signal cancelReservationRequested(string reservationId)

    function openCreateReservationDialog(itemFilterValue, storeroomFilterValue) {
        root.createTarget = {
            "state": {
                "stockItemId": String(itemFilterValue || "") === "all" ? "" : String(itemFilterValue || ""),
                "storeroomId": String(storeroomFilterValue || "") === "all" ? "" : String(storeroomFilterValue || "")
            }
        }
        createDialog.reservationData = root.createTarget
        createDialog.open()
    }

    function openIssueReservationDialog(reservationData) {
        root.issueTarget = reservationData || ({})
        issueDialog.reservationData = root.issueTarget
        issueDialog.open()
    }

    function openReleaseConfirmation(reservationData) {
        root.confirmationTarget = reservationData || ({})
        root.confirmationMode = "release"
        confirmationDialog.title = "Release Reservation"
        confirmationMessage.text = "Release the remaining quantity on this reservation?"
        confirmationDialog.open()
    }

    function openCancelConfirmation(reservationData) {
        root.confirmationTarget = reservationData || ({})
        root.confirmationMode = "cancel"
        confirmationDialog.title = "Cancel Reservation"
        confirmationMessage.text = "Cancel this reservation and return the remaining quantity to availability?"
        confirmationDialog.open()
    }

    InventoryDialogs.ReservationCreateDialog {
        id: createDialog
        objectName: "reservationCreateDialog"

        itemOptions: root.itemOptions
        storeroomOptions: root.storeroomOptions

        onSubmitted: function(payload) {
            root.createReservationRequested(payload)
            createDialog.close()
        }
    }

    InventoryDialogs.ReservationIssueDialog {
        id: issueDialog
        objectName: "reservationIssueDialog"

        onSubmitted: function(payload) {
            root.issueReservationRequested(payload)
            issueDialog.close()
        }
    }

    AppWidgets.EntityDialog {
        id: confirmationDialog
        objectName: "reservationConfirmationDialog"
        title:       root.confirmationMode === "cancel" ? "Cancel Reservation" : "Release Reservation"
        subtitle:    confirmationMessage.text
        primaryText: root.confirmationMode === "cancel" ? "Cancel Reservation" : "Release Reservation"
        primaryIcon: root.confirmationMode === "cancel" ? "close" : "approve"

        onAccepted: {
            var state = root.confirmationTarget && root.confirmationTarget.state ? root.confirmationTarget.state : (root.confirmationTarget || {})
            var reservationId = String(state.reservationId || "")
            if (root.confirmationMode === "release" && reservationId.length > 0) {
                root.releaseReservationRequested(reservationId)
            } else if (root.confirmationMode === "cancel" && reservationId.length > 0) {
                root.cancelReservationRequested(reservationId)
            }
            confirmationDialog.close()
        }
        onRejected: confirmationDialog.close()

        // Message ID kept for external text assignment
        AppControls.Label { id: confirmationMessage; visible: false; text: "" }
    }
}

