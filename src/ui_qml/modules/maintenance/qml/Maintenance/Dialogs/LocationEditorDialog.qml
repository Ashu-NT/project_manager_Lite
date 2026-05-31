import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Location"
    property var recordState: ({})
    property var siteOptions: []
    property var parentLocationOptions: []
    property var statusOptions: []
    property var criticalityOptions: []

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Location"
        ? "Capture site location hierarchy, lifecycle state, and scope notes for maintenance anchors."
        : "Update the location record, hierarchy context, and lifecycle state."
    errorMessage: root.validationMessage
    primaryText:  root.modeTitle === "Create Location" ? "Create Location" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Location" ? "add" : "save"
    width: 720

    onOpened:   root.populateFromRecord()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromRecord() {
        const state = root.recordState || {}
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        parentLocationCombo.currentIndex = root.indexForValue(root.parentLocationOptions, state.parentLocationId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        criticalityCombo.currentIndex = root.indexForValue(root.criticalityOptions, state.criticality || "MEDIUM")
        locationCodeField.text = String(state.locationCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        locationTypeField.text = String(state.locationType || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedParent = root.parentLocationOptions[parentLocationCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedCriticality = root.criticalityOptions[criticalityCombo.currentIndex] || { "value": "MEDIUM" }
        return {
            "locationId": String(state.locationId || ""),
            "siteId": String(selectedSite.value || ""),
            "locationCode": locationCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "parentLocationId": String(selectedParent.value || ""),
            "locationType": locationTypeField.text,
            "criticality": String(selectedCriticality.value || "MEDIUM"),
            "status": String(selectedStatus.value || "ACTIVE"),
            "isActive": activeCheck.checked,
            "notes": notesField.text,
            "expectedVersion": Number(state.expectedVersion || 0)
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a site before saving."
            return
        }
        if (locationCodeField.text.trim().length === 0) {
            root.validationMessage = "Location code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Location name is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 640 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Site" }
        AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

        AppControls.Label { text: "Location code" }
        AppControls.TextField { id: locationCodeField; Layout.fillWidth: true; placeholderText: "LOC-100" }

        AppControls.Label { text: "Name" }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Production Area A" }

        AppControls.Label { text: "Parent location" }
        AppControls.ComboBox { id: parentLocationCombo; Layout.fillWidth: true; model: root.parentLocationOptions; textRole: "label" }

        AppControls.Label { text: "Location type" }
        AppControls.TextField { id: locationTypeField; Layout.fillWidth: true; placeholderText: "PRODUCTION" }

        AppControls.Label { text: "Criticality" }
        AppControls.ComboBox { id: criticalityCombo; Layout.fillWidth: true; model: root.criticalityOptions; textRole: "label" }

        AppControls.Label { text: "Lifecycle status" }
        AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.statusOptions; textRole: "label" }
    }

    AppControls.Label { text: "Description" }
    AppControls.TextArea {
        id: descriptionField
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        wrapMode: TextEdit.WordWrap
    }

    AppControls.CheckBox { id: activeCheck; text: "Active location" }

    AppControls.Label { text: "Notes" }
    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        wrapMode: TextEdit.WordWrap
    }
}
