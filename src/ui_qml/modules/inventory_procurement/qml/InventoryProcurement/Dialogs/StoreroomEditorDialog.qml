import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property string modeTitle: "Create Storeroom"
    property var siteOptions: []
    property var statusOptions: []
    property var managerPartyOptions: []
    property var storeroomData: ({})
    property string validationMessage: ""
    readonly property var formSiteOptions: siteOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 760
    height: Math.min(860, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 860)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromStoreroom() {
        var state = root.storeroomData && root.storeroomData.state ? root.storeroomData.state : (root.storeroomData || {})
        storeroomCodeField.text = String(state.storeroomCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        siteCombo.currentIndex = root.indexForValue(root.formSiteOptions, state.siteId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "")
        storeroomTypeField.text = String(state.storeroomType || "")
        defaultCurrencyField.text = String(state.defaultCurrencyCode || "")
        managerPartyCombo.currentIndex = root.indexForValue(root.managerPartyOptions, state.managerPartyId || "")
        internalSupplierCheck.checked = state.isInternalSupplier === true
        allowsIssueCheck.checked = state.allowsIssue !== false
        allowsTransferCheck.checked = state.allowsTransfer !== false
        allowsReceivingCheck.checked = state.allowsReceiving !== false
        requiresReservationCheck.checked = state.requiresReservationForIssue === true
        requiresSupplierReferenceCheck.checked = state.requiresSupplierReferenceForReceipt === true
        notesField.text = String(state.notes || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        var selectedSite = root.formSiteOptions[siteCombo.currentIndex] || { "value": "" }
        var selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "" }
        var selectedParty = root.managerPartyOptions[managerPartyCombo.currentIndex] || { "value": "" }
        return {
            "storeroomCode": storeroomCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "siteId": String(selectedSite.value || ""),
            "status": String(selectedStatus.value || ""),
            "storeroomType": storeroomTypeField.text,
            "defaultCurrencyCode": defaultCurrencyField.text,
            "managerPartyId": String(selectedParty.value || ""),
            "isInternalSupplier": internalSupplierCheck.checked,
            "allowsIssue": allowsIssueCheck.checked,
            "allowsTransfer": allowsTransferCheck.checked,
            "allowsReceiving": allowsReceivingCheck.checked,
            "requiresReservationForIssue": requiresReservationCheck.checked,
            "requiresSupplierReferenceForReceipt": requiresSupplierReferenceCheck.checked,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (storeroomCodeField.text.trim().length === 0) {
            root.validationMessage = "Storeroom code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Storeroom name is required."
            return
        }
        if (String((root.formSiteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a site before saving."
            return
        }
        if (String((root.statusOptions[statusCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a storeroom status before saving."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromStoreroom()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: root.modeTitle === "Create Storeroom"
                    ? "Create an operational stock location with capability flags, ownership, and receipt policy."
                    : "Update storeroom governance, capability flags, manager ownership, and receipt policy."
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
                columns: root.width > 680 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Storeroom code" }
                TextField { id: storeroomCodeField; Layout.fillWidth: true; placeholderText: "MAIN" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Main Storeroom" }

                Label { text: "Site" }
                ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.formSiteOptions; textRole: "label" }

                Label { text: "Status" }
                ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }

                Label { text: "Storeroom type" }
                TextField { id: storeroomTypeField; Layout.fillWidth: true; placeholderText: "MAIN" }

                Label { text: "Default currency" }
                TextField { id: defaultCurrencyField; Layout.fillWidth: true; placeholderText: "EUR" }

                Label { text: "Manager party" }
                ComboBox { id: managerPartyCombo; Layout.fillWidth: true; model: root.managerPartyOptions; textRole: "label" }
            }

            CheckBox { id: internalSupplierCheck; text: "Storeroom acts as an internal supplier" }
            CheckBox { id: allowsIssueCheck; text: "Allow issue transactions" }
            CheckBox { id: allowsTransferCheck; text: "Allow transfer transactions" }
            CheckBox { id: allowsReceivingCheck; text: "Allow receiving transactions" }
            CheckBox { id: requiresReservationCheck; text: "Require reservations before issue" }
            CheckBox { id: requiresSupplierReferenceCheck; text: "Require supplier reference for receipts" }

            Label {
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
                placeholderText: "Optional storeroom description"
            }

            Label {
                text: "Notes"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
                placeholderText: "Receiving or routing notes"
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

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

