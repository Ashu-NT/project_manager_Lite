import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var reservationData: ({})
    property string validationMessage: ""
    readonly property var formItemOptions: itemOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })
    readonly property var formStoreroomOptions: storeroomOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 720
    title: "Create Reservation"
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromReservation() {
        var state = root.reservationData && root.reservationData.state ? root.reservationData.state : (root.reservationData || {})
        itemCombo.currentIndex = root.indexForValue(root.formItemOptions, state.stockItemId || "")
        storeroomCombo.currentIndex = root.indexForValue(root.formStoreroomOptions, state.storeroomId || "")
        quantityField.text = ""
        needByDateField.text = ""
        sourceTypeField.text = String(state.sourceReferenceType || "")
        sourceIdField.text = String(state.sourceReferenceId || "")
        notesField.text = ""
        root.validationMessage = ""
    }

    function buildPayload() {
        var selectedItem = root.formItemOptions[itemCombo.currentIndex] || { "value": "" }
        var selectedStoreroom = root.formStoreroomOptions[storeroomCombo.currentIndex] || { "value": "" }
        return {
            "stockItemId": String(selectedItem.value || ""),
            "storeroomId": String(selectedStoreroom.value || ""),
            "reservedQty": quantityField.text,
            "needByDate": needByDateField.text,
            "sourceReferenceType": sourceTypeField.text,
            "sourceReferenceId": sourceIdField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.formItemOptions[itemCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose an item before saving."
            return
        }
        if (String((root.formStoreroomOptions[storeroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a storeroom before saving."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.validationMessage = "Reserved quantity must be greater than zero."
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

        AppControls.Label {
            Layout.fillWidth: true
            text: "Reserve available stock against a real upstream demand reference. The reservation reduces availability without reducing on-hand stock."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
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
            columns: root.width > 620 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            AppControls.Label { text: "Item" }
            AppControls.ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.formItemOptions; textRole: "label" }

            AppControls.Label { text: "Storeroom" }
            AppControls.ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.formStoreroomOptions; textRole: "label" }

            AppControls.Label { text: "Reserved qty" }
            AppControls.TextField { id: quantityField; objectName: "quantityField"; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

            AppControls.Label { text: "Need by (YYYY-MM-DD)" }
            AppControls.DateField { id: needByDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }

            AppControls.Label { text: "Source type" }
            AppControls.TextField { id: sourceTypeField; Layout.fillWidth: true; placeholderText: "task, work_order, project..." }

            AppControls.Label { text: "Source id" }
            AppControls.TextField { id: sourceIdField; Layout.fillWidth: true; placeholderText: "TASK-42" }
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
            placeholderText: "Reservation context, scope, or issuing notes."
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Save"
            iconName: "save"
            onClicked: root.submitDialog()
        }
    }
}

