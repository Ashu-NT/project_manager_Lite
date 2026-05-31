import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create System"
    property var recordState: ({})
    property var siteOptions: []
    property var locationOptions: []
    property var parentSystemOptions: []
    property var statusOptions: []
    property var criticalityOptions: []
    property string validationMessage: ""

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create System"
        ? "Capture system hierarchy and lifecycle state for maintenance planning scope."
        : "Update the system record, hierarchy context, and lifecycle state."
    errorMessage: root.validationMessage
    primaryText:  root.modeTitle === "Create System" ? "Create System" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create System" ? "add" : "save"
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
        locationCombo.currentIndex = root.indexForValue(root.locationOptions, state.locationId || "")
        parentSystemCombo.currentIndex = root.indexForValue(root.parentSystemOptions, state.parentSystemId || "")
        statusCombo.currentIndex = root.indexForValue(root.statusOptions, state.status || "ACTIVE")
        criticalityCombo.currentIndex = root.indexForValue(root.criticalityOptions, state.criticality || "MEDIUM")
        systemCodeField.text = String(state.systemCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        systemTypeField.text = String(state.systemType || "")
        notesField.text = String(state.notes || "")
        activeCheck.checked = state.isActive === undefined ? true : !!state.isActive
        root.validationMessage = ""
    }

    function buildPayload() {
        const state = root.recordState || {}
        const selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        const selectedLocation = root.locationOptions[locationCombo.currentIndex] || { "value": "" }
        const selectedParent = root.parentSystemOptions[parentSystemCombo.currentIndex] || { "value": "" }
        const selectedStatus = root.statusOptions[statusCombo.currentIndex] || { "value": "ACTIVE" }
        const selectedCriticality = root.criticalityOptions[criticalityCombo.currentIndex] || { "value": "MEDIUM" }
        return {
            "systemId": String(state.systemId || ""),
            "siteId": String(selectedSite.value || ""),
            "locationId": String(selectedLocation.value || ""),
            "systemCode": systemCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "parentSystemId": String(selectedParent.value || ""),
            "systemType": systemTypeField.text,
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
        if (systemCodeField.text.trim().length === 0) {
            root.validationMessage = "System code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "System name is required."
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

        AppControls.Label { text: "System code" }
        AppControls.TextField { id: systemCodeField; Layout.fillWidth: true; placeholderText: "SYS-100" }

        AppControls.Label { text: "Name" }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Packaging Line" }

        AppControls.Label { text: "Location" }
        AppControls.ComboBox { id: locationCombo; Layout.fillWidth: true; model: root.locationOptions; textRole: "label" }

        AppControls.Label { text: "Parent system" }
        AppControls.ComboBox { id: parentSystemCombo; Layout.fillWidth: true; model: root.parentSystemOptions; textRole: "label" }

        AppControls.Label { text: "System type" }
        AppControls.TextField { id: systemTypeField; Layout.fillWidth: true; placeholderText: "LINE" }

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

    AppControls.CheckBox { id: activeCheck; text: "Active system" }

    AppControls.Label { text: "Notes" }
    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        wrapMode: TextEdit.WordWrap
    }
}
