import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var reservationData: ({})

    signal submitted(var payload)

    width: 560
    title: "Issue Reservation"
    subtitle: "Issue reserved stock to the requesting work order or project."
    primaryText: "Issue Stock"
    primaryIcon: "approve"
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function populateFromReservation() {
        var state = root.reservationData && root.reservationData.state ? root.reservationData.state : (root.reservationData || {})
        quantityField.text = String(state.remainingQty || "")
        notesField.text = ""
        root.validationMessage = ""
    }

    function buildPayload() {
        var state = root.reservationData && root.reservationData.state ? root.reservationData.state : (root.reservationData || {})
        return {
            "reservationId": String(state.reservationId || ""),
            "quantity": quantityField.text,
            "note": notesField.text
        }
    }

    function submitDialog() {
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.validationMessage = "Issue quantity must be greater than zero."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromReservation()

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Reservation" }
        AppControls.Label {
            Layout.fillWidth: true
            text: String(root.reservationData.title || "")
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            wrapMode: Text.WordWrap
        }

        AppControls.Label { text: "Remaining qty" }
        AppControls.Label {
            Layout.fillWidth: true
            text: String(root.reservationData.state && root.reservationData.state.remainingQtyLabel || "-")
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            wrapMode: Text.WordWrap
        }

        AppControls.Label { text: "Issue qty" }
        AppControls.TextField {
            id: quantityField
            Layout.fillWidth: true
            placeholderText: "1.000"
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }
    }

    AppControls.Label {
        text: "Notes"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 96
        wrapMode: TextEdit.WordWrap
        placeholderText: "Issuing context or execution note."
    }
}
