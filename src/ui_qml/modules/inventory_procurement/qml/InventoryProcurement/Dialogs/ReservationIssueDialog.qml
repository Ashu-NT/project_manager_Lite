import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var reservationData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 560
    title: "Issue Reservation"
    closePolicy: Popup.CloseOnEscape

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

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Issue reserved stock against the held quantity. This reduces on-hand stock and consumes the reservation at the same time."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: root.validationMessage.length > 0
            text: root.validationMessage
            color: "#8B1E1E"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Reservation" }
            Label {
                Layout.fillWidth: true
                text: String(root.reservationData.title || "")
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                wrapMode: Text.WordWrap
            }

            Label { text: "Remaining qty" }
            Label {
                Layout.fillWidth: true
                text: String(root.reservationData.state && root.reservationData.state.remainingQtyLabel || "-")
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                wrapMode: Text.WordWrap
            }

            Label { text: "Issue qty" }
            TextField {
                id: quantityField
                Layout.fillWidth: true
                placeholderText: "1.000"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
        }

        Label {
            text: "Notes"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            wrapMode: TextEdit.WordWrap
            placeholderText: "Issuing context or execution note."
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Issue"
            onClicked: root.submitDialog()
        }
    }
}
