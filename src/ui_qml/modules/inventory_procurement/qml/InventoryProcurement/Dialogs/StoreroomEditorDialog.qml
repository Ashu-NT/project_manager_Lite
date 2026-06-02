import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Storeroom"
    property var siteOptions: []
    property var statusOptions: []
    property var managerPartyOptions: []
    property var storeroomData: ({})
    property var workspaceController: null
    property string storeroomCode: ""
    readonly property var formSiteOptions: siteOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    width: 760
    title: root.modeTitle
    subtitle: root.modeTitle === "Create Storeroom"
        ? "Create an operational stock location with capability flags, ownership, and receipt policy."
        : "Update storeroom governance, capability flags, manager ownership, and receipt policy."
    primaryText: root.modeTitle === "Create Storeroom" ? "Create Storeroom" : "Save Changes"
    primaryIcon: root.modeTitle === "Create Storeroom" ? "add" : "save"
    onAccepted: root.submitDialog()
    onRejected: root.close()

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
        root.storeroomCode = String(state.storeroomCode || "")
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
        root.errorMessage = ""
    }

    function buildPayload() {
        var selectedSite = root.formSiteOptions[siteCombo.currentIndex] || { "value": "" }
        var selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "" }
        var selectedParty = root.managerPartyOptions[managerPartyCombo.currentIndex] || { "value": "" }
        return {
            "storeroomCode": root.storeroomCode,
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
        if (root.storeroomCode.trim().length === 0) {
            root.errorMessage = "Storeroom code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Storeroom name is required."
            return
        }
        if (String((root.formSiteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a site before saving."
            return
        }
        if (String((root.statusOptions[statusCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a storeroom status before saving."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromStoreroom()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 680 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            label: "Storeroom code"
            value: root.storeroomCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.busy
            onValueEdited: function(code) { root.storeroomCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("storeroom", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.storeroomCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Name"
            required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Main Storeroom" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Site"
            required: true
            AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.formSiteOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Status"
            required: true
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Storeroom type"
            AppControls.TextField { id: storeroomTypeField; Layout.fillWidth: true; placeholderText: "MAIN" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Default currency"
            AppControls.TextField { id: defaultCurrencyField; Layout.fillWidth: true; placeholderText: "EUR" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Manager party"
            AppControls.ComboBox { id: managerPartyCombo; Layout.fillWidth: true; model: root.managerPartyOptions; textRole: "label" }
        }
    }

    AppControls.CheckBox { id: internalSupplierCheck; text: "Storeroom acts as an internal supplier" }
    AppControls.CheckBox { id: allowsIssueCheck; text: "Allow issue transactions" }
    AppControls.CheckBox { id: allowsTransferCheck; text: "Allow transfer transactions" }
    AppControls.CheckBox { id: allowsReceivingCheck; text: "Allow receiving transactions" }
    AppControls.CheckBox { id: requiresReservationCheck; text: "Require reservations before issue" }
    AppControls.CheckBox { id: requiresSupplierReferenceCheck; text: "Require supplier reference for receipts" }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 88
            wrapMode: TextEdit.WordWrap
            placeholderText: "Optional storeroom description"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"
        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 88
            wrapMode: TextEdit.WordWrap
            placeholderText: "Receiving or routing notes"
        }
    }
}
